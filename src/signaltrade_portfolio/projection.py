from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

DEFAULT_FEE_RATE = 0.0005


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


@dataclass(frozen=True, slots=True)
class ProjectedEvent:
    entry_price: float | None
    transaction_amount: float
    fee: float
    realized_profit_loss: float | None


@dataclass(frozen=True, slots=True)
class LedgerProjection:
    position: CalculatedPosition
    realized_profit_loss: float
    sold_cost_basis: float
    events: dict[int, ProjectedEvent]


def project_ledger(
    events: Iterable[PositionEvent],
    *,
    include_buy_fees_in_cost: bool,
    fee_rate: float = DEFAULT_FEE_RATE,
) -> LedgerProjection:
    volume = cost = gross_cost = realized = sold_cost_basis = 0.0
    projected: dict[int, ProjectedEvent] = {}
    for event in sorted(events, key=lambda item: (item.occurred_at, item.source_id, item.kind)):
        quantity = max(0.0, float(event.volume))
        if quantity <= 0:
            continue
        price = float(event.price or 0)
        amount = quantity * price
        fee = 0.0
        if event.kind in {"execution_buy", "execution_sell"}:
            fee = float(event.paid_fee) if event.paid_fee is not None else amount * fee_rate
        if event.kind == "execution_buy":
            if price <= 0:
                continue
            volume += quantity
            gross_cost += amount
            cost += amount + (fee if include_buy_fees_in_cost else 0.0)
            projected[event.source_id] = ProjectedEvent(price, amount, fee, None)
            continue
        if event.kind not in {"execution_sell", "deduct"} or volume <= 0:
            if event.kind == "execution_sell":
                projected[event.source_id] = ProjectedEvent(None, amount, fee, None)
            continue
        removed = min(quantity, volume)
        average_cost = cost / volume
        average_entry = gross_cost / volume
        removed_cost = removed * average_cost
        removed_gross_cost = removed * average_entry
        event_realized = None
        if event.kind == "execution_sell":
            event_realized = removed * price - fee * (removed / quantity) - removed_cost
            realized += event_realized
            sold_cost_basis += removed_cost
            projected[event.source_id] = ProjectedEvent(
                average_entry, amount, fee, event_realized
            )
        volume -= removed
        cost = max(0.0, cost - removed_cost)
        gross_cost = max(0.0, gross_cost - removed_gross_cost)
    position = (
        CalculatedPosition(0.0, 0.0, None)
        if volume <= 1e-12
        else CalculatedPosition(volume, cost, cost / volume)
    )
    return LedgerProjection(position, realized, sold_cost_basis, projected)


def project_position(events: Iterable[PositionEvent]) -> CalculatedPosition:
    return project_ledger(events, include_buy_fees_in_cost=False).position
