from signaltrade_portfolio.models import PositionSyncAdjustment
from signaltrade_portfolio.reconciliation import (
    actual_coin_totals, recorded_strategy_positions, recorded_strategy_volumes,
)
from signaltrade_portfolio.reconciliation_events import enqueue_position_reconciled


class PositionDeductionError(ValueError):
    pass


def apply_position_deduction(db, *, user_id: int, accounts: list[dict],
                             subscription_id: int, volume: float, source: str,
                             idempotency_key: str | None = None) -> PositionSyncAdjustment:
    if volume <= 0:
        raise PositionDeductionError("차감 수량은 0보다 커야 합니다.")
    if idempotency_key:
        existing = db.query(PositionSyncAdjustment).filter_by(
            idempotency_key=idempotency_key).first()
        if existing is not None:
            return existing
    selected = next((row for row in recorded_strategy_positions(db, user_id)
                     if row["subscription_id"] == subscription_id), None)
    if selected is None:
        raise PositionDeductionError("실전 전략 설정을 찾을 수 없습니다.")
    currency = selected["market"].split("-", 1)[-1]
    actual_total = actual_coin_totals(accounts).get(currency, 0.0)
    strategy_total = recorded_strategy_volumes(db, user_id).get(currency, 0.0)
    difference = actual_total - strategy_total
    tolerance = max(1e-8, abs(difference) * 1e-6)
    if difference >= -tolerance:
        raise PositionDeductionError("실제 잔고 부족 수량이 있는 경우에만 차감할 수 있습니다.")
    if volume > -difference + tolerance:
        raise PositionDeductionError("차감 수량이 실제 잔고 부족 수량보다 큽니다.")
    if volume > selected["volume"] + tolerance:
        raise PositionDeductionError("선택한 전략의 보유 수량보다 많이 차감할 수 없습니다.")
    adjustment = PositionSyncAdjustment(
        user_id=user_id, user_strategy_id=subscription_id, currency=currency,
        action="deduct", volume=volume,
        reference_price=float(selected["average_buy_price"] or 0),
        cost_basis_source="strategy_average_cost", difference_before=difference,
        source=source, reason="실제 잔고 부족분을 전략에서 차감",
        idempotency_key=idempotency_key)
    db.add(adjustment)
    enqueue_position_reconciled(db, adjustment)
    return adjustment
