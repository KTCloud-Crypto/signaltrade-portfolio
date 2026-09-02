from dataclasses import dataclass


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
