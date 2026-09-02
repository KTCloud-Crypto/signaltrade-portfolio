from dataclasses import dataclass
from datetime import datetime
from typing import Iterable


@dataclass(frozen=True, slots=True)
class PositionEvent:
    kind: str
    volume: float
    price: float | None
    occurred_at: datetime
    source_id: int
    paid_fee: float | None = None


@dataclass(frozen=True, slots=True)
class CalculatedPosition:
    volume: float
    cost_basis: float
    average_buy_price: float | None


def project_position(events: Iterable[PositionEvent]) -> CalculatedPosition:
    volume = 0.0
    cost = 0.0
    for event in sorted(events, key=lambda item: (item.occurred_at, item.source_id, item.kind)):
        quantity = max(0.0, float(event.volume))
        if quantity <= 0:
            continue
        if event.kind == "execution_buy" and event.price and event.price > 0:
            volume += quantity
            cost += quantity * float(event.price)
        elif event.kind in {"execution_sell", "deduct"} and volume > 0:
            removed = min(quantity, volume)
            cost = max(0.0, cost - removed * (cost / volume))
            volume -= removed
    if volume <= 1e-12:
        return CalculatedPosition(0.0, 0.0, None)
    return CalculatedPosition(volume, cost, cost / volume)
