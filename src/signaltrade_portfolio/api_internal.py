import hmac
from decimal import Decimal, ROUND_DOWN

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select

from signaltrade_portfolio.config import settings
from signaltrade_portfolio.database import get_db
from signaltrade_portfolio.models import (
    paper_account_table, strategy_table, supported_market_table, user_strategy_table,
)
from signaltrade_portfolio.positions import load_strategy_position
from signaltrade_portfolio.identity_client import get_exchange_credentials
from signaltrade_portfolio.upbit_accounts import get_accounts
from signaltrade_portfolio.reconciliation import actual_coin_totals, recorded_strategy_volumes


def require_internal_service_token(
    token: str | None = Header(default=None, alias="X-SignalTrade-Service-Token"),
):
    expected = settings.internal_service_token
    if not expected or not token or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="유효한 내부 서비스 토큰이 필요합니다.")


router = APIRouter(prefix="/internal/portfolio", tags=["Portfolio Internal"],
                   dependencies=[Depends(require_internal_service_token)])
FEE_BUFFER_RATE = Decimal("0.0005")


def _available_strategy_cash(db, user_id: int, mode: str,
                             exclude_subscription_id: int | None = None) -> dict[str, float]:
    if mode == "simulated":
        cash = db.execute(select(paper_account_table.c.cash_balance).where(
            paper_account_table.c.user_id == user_id)).scalar_one_or_none()
        balance = Decimal(str(cash or 0))
    else:
        krw = next((row for row in user_balance(user_id) if row["currency"] == "KRW"), None)
        balance = Decimal(str(krw["balance"] if krw else 0))

    us = user_strategy_table
    query = select(us.c.id, us.c.allocated_amount).where(
        us.c.user_id == user_id, us.c.mode == mode, us.c.enabled.is_(True),
        us.c.allocated_amount.is_not(None),
    )
    if exclude_subscription_id is not None:
        query = query.where(us.c.id != exclude_subscription_id)
    reserved = sum((Decimal(str(row.allocated_amount)) for row in db.execute(query)
                    if load_strategy_position(db, row.id, mode).volume <= 0), Decimal("0"))
    available = max(Decimal("0"), balance - reserved) / (Decimal("1") + FEE_BUFFER_RATE)
    available = available.quantize(Decimal("1"), rounding=ROUND_DOWN)
    return {"cash_balance": float(balance), "reserved_amount": float(reserved),
            "available_cash": float(available)}


@router.get("/users/{user_id}/strategy-cash")
def strategy_cash(user_id: int, mode: str = Query(pattern="^(simulated|live)$"),
                  exclude_subscription_id: int | None = Query(default=None), db=Depends(get_db)) -> dict[str, float]:
    return _available_strategy_cash(db, user_id, mode, exclude_subscription_id)


@router.get("/users/{user_id}/open-positions")
def open_positions(user_id: int, db=Depends(get_db)) -> list[dict]:
    us, st, market = user_strategy_table, strategy_table, supported_market_table
    rows = db.execute(select(us.c.id, us.c.mode, st.c.id.label("strategy_id"),
        st.c.name.label("strategy_name"), st.c.code.label("strategy_code"),
        market.c.code.label("market")).select_from(
            us.join(st, st.c.id == us.c.strategy_id).join(market, market.c.id == us.c.market_id)
        ).where(us.c.user_id == user_id, us.c.enabled.is_(True), st.c.enabled.is_(True))).all()
    result = []
    for row in rows:
        position = load_strategy_position(db, row.id, row.mode)
        if position.volume > 0:
            result.append({"subscription_id": row.id, "strategy_id": row.strategy_id,
                "strategy_name": row.strategy_name, "strategy_code": row.strategy_code,
                "market": row.market, "mode": row.mode, "volume": position.volume,
                "average_buy_price": position.average_buy_price})
    return result


@router.get("/markets/{market}/open-positions")
def market_open_positions(market: str, db=Depends(get_db)) -> list[dict]:
    us, st, supported_market = user_strategy_table, strategy_table, supported_market_table
    rows = db.execute(
        select(us.c.id, us.c.user_id, us.c.mode)
        .select_from(
            us.join(st, st.c.id == us.c.strategy_id).join(
                supported_market, supported_market.c.id == us.c.market_id
            )
        )
        .where(
            supported_market.c.code == market.upper(),
            us.c.enabled.is_(True),
            st.c.enabled.is_(True),
        )
    ).all()
    result = []
    for row in rows:
        position = load_strategy_position(db, row.id, row.mode)
        if position.volume > 0 and position.average_buy_price:
            result.append({
                "subscription_id": row.id,
                "user_id": row.user_id,
                "mode": row.mode,
                "volume": position.volume,
                "average_buy_price": position.average_buy_price,
            })
    return result


@router.get("/users/{user_id}/balance")
def user_balance(user_id: int) -> list[dict]:
    credentials = get_exchange_credentials(user_id)
    return get_accounts(access_key=credentials.access_key, secret_key=credentials.secret_key,
                        base_url=settings.upbit_api_base_url,
                        timeout=settings.upbit_api_timeout_seconds)


@router.get("/users/{user_id}/reconciliation-state")
def user_reconciliation_state(user_id: int, db=Depends(get_db)) -> dict[str, dict[str, float]]:
    accounts = user_balance(user_id)
    actual = actual_coin_totals(accounts)
    recorded = recorded_strategy_volumes(db, user_id)
    return {
        currency: {
            "actual_total": actual.get(currency, 0.0),
            "strategy_volume": recorded.get(currency, 0.0),
            "difference": actual.get(currency, 0.0) - recorded.get(currency, 0.0),
        }
        for currency in sorted(set(actual) | set(recorded))
    }
