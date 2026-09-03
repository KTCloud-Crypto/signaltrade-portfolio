import hashlib

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select

from signaltrade_portfolio.database import get_db
from signaltrade_portfolio.deductions import PositionDeductionError, apply_position_deduction
from signaltrade_portfolio.identity_client import (
    AuthenticatedUser, get_current_user, get_exchange_credentials,
)
from signaltrade_portfolio.models import PositionSyncAdjustment, user_table
from signaltrade_portfolio.reconciliation import (
    actual_coin_totals, calculate_reconciliation_state, recorded_strategy_positions,
    recorded_strategy_volumes,
)
from signaltrade_portfolio.upbit_accounts import get_accounts
from signaltrade_portfolio.config import settings


class PositionDeductionIn(BaseModel):
    subscription_id: int
    volume: float = Field(gt=0)


class PositionDeductionBatchIn(BaseModel):
    currency: str = Field(min_length=2, max_length=16)
    expected_difference: float
    deductions: list[PositionDeductionIn] = Field(min_length=1)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=64)


router = APIRouter(prefix="/positions/reconciliation", tags=["Portfolio Reconciliation"])


def _accounts(user_id: int) -> list[dict]:
    credentials = get_exchange_credentials(user_id)
    return get_accounts(access_key=credentials.access_key, secret_key=credentials.secret_key,
                        base_url=settings.upbit_api_base_url,
                        timeout=settings.upbit_api_timeout_seconds)


@router.get("")
def reconciliation(user: AuthenticatedUser = Depends(get_current_user), db=Depends(get_db)) -> list[dict]:
    accounts = _accounts(user.id)
    actual = actual_coin_totals(accounts)
    positions = recorded_strategy_positions(db, user.id)
    recorded = recorded_strategy_volumes(db, user.id)
    result = []
    for currency in sorted(set(actual) | set(recorded)):
        state = calculate_reconciliation_state(actual.get(currency, 0.0), recorded.get(currency, 0.0))
        result.append({"currency": currency, "actual_total": state.actual_total,
                       "strategy_volume": state.strategy_volume, "difference": state.difference,
                       "status": state.status,
                       "strategies": [row for row in positions
                                      if row["market"].endswith(f"-{currency}")]})
    return result


@router.post("/deduct", status_code=204)
def deduct(payload: PositionDeductionBatchIn,
           user: AuthenticatedUser = Depends(get_current_user), db=Depends(get_db)) -> Response:
    currency = payload.currency.upper()
    if len({row.subscription_id for row in payload.deductions}) != len(payload.deductions):
        raise HTTPException(409, "동일한 전략을 중복 선택할 수 없습니다.")
    keys = ([hashlib.sha256(f"{payload.idempotency_key}:{index}".encode()).hexdigest()
             for index in range(len(payload.deductions))] if payload.idempotency_key else [])
    if keys:
        existing = db.query(PositionSyncAdjustment).filter(
            PositionSyncAdjustment.idempotency_key.in_(keys)).count()
        if existing == len(keys):
            return Response(status_code=204)
        if existing:
            raise HTTPException(409, "일부 차감만 기록된 요청입니다. 관리자 확인이 필요합니다.")
    db.execute(select(user_table.c.id).where(user_table.c.id == user.id).with_for_update()).one()
    accounts = _accounts(user.id)
    actual = actual_coin_totals(accounts).get(currency, 0.0)
    strategy_total = recorded_strategy_volumes(db, user.id).get(currency, 0.0)
    difference = actual - strategy_total
    tolerance = max(1e-8, strategy_total * 1e-4)
    if difference >= -tolerance:
        raise HTTPException(409, "현재 차감할 실제 잔고 부족분이 없습니다.")
    if abs(payload.expected_difference - difference) > tolerance:
        raise HTTPException(409, "잔고 상태가 변경되었습니다. 새로고침 후 다시 시도해 주세요.")
    if sum(row.volume for row in payload.deductions) > -difference + tolerance:
        raise HTTPException(409, "전체 차감 수량이 현재 부족 수량보다 큽니다.")
    positions = {row["subscription_id"]: row for row in recorded_strategy_positions(db, user.id)}
    for item in payload.deductions:
        selected = positions.get(item.subscription_id)
        if selected is None or not selected["market"].endswith(f"-{currency}"):
            raise HTTPException(409, "선택한 종목의 실전 전략이 아닙니다.")
        if item.volume > selected["volume"] + tolerance:
            raise HTTPException(409, "전략 보유 수량보다 많이 차감할 수 없습니다.")
    try:
        for index, item in enumerate(payload.deductions):
            apply_position_deduction(db, user_id=user.id, accounts=accounts,
                                     subscription_id=item.subscription_id, volume=item.volume,
                                     source="web", idempotency_key=keys[index] if keys else None)
        db.commit()
    except PositionDeductionError as error:
        db.rollback()
        raise HTTPException(409, str(error)) from error
    return Response(status_code=204)
