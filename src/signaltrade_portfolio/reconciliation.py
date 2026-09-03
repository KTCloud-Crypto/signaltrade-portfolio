from dataclasses import dataclass

from sqlalchemy import select

from signaltrade_portfolio.models import (
    strategy_table, supported_market_table, user_strategy_table,
)
from signaltrade_portfolio.positions import load_strategy_position


@dataclass(frozen=True, slots=True)
class ReconciliationState:
    actual_total: float
    strategy_volume: float
    difference: float
    unallocated_volume: float
    shortfall_volume: float
    status: str


def actual_coin_totals(accounts: list[dict]) -> dict[str, float]:
    return {row["currency"]: float(row["balance"]) + float(row["locked"])
            for row in accounts if row["currency"] != "KRW"}


def calculate_reconciliation_state(actual_total: float,
                                   strategy_volume: float) -> ReconciliationState:
    tolerance = max(1e-8, strategy_volume * 1e-4)
    difference = actual_total - strategy_volume
    status = "matched" if abs(difference) <= tolerance else (
        "external_balance" if difference > 0 else "shortfall")
    return ReconciliationState(actual_total, strategy_volume, difference,
                               max(difference, 0.0), max(-difference, 0.0), status)


def recorded_strategy_volumes(db, user_id: int) -> dict[str, float]:
    us, st, market = user_strategy_table, strategy_table, supported_market_table
    rows = db.execute(select(us.c.id, market.c.code).select_from(
        us.join(st, st.c.id == us.c.strategy_id).join(market, market.c.id == us.c.market_id)
    ).where(us.c.user_id == user_id, us.c.mode == "live",
            st.c.code != "manual_hold_v1")).all()
    totals: dict[str, float] = {}
    for row in rows:
        currency = row.code.split("-", 1)[-1]
        totals[currency] = totals.get(currency, 0.0) + load_strategy_position(
            db, row.id, "live").volume
    return totals
