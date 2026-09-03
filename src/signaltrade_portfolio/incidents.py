from datetime import datetime

from signaltrade_portfolio.models import PositionMismatchIncident
from signaltrade_portfolio.reconciliation import calculate_reconciliation_state


def record_currency_state(db, *, user_id: int, currency: str, actual_total: float,
                          strategy_volume: float, now: datetime | None = None) -> PositionMismatchIncident | None:
    current_time = now or datetime.utcnow()
    state = calculate_reconciliation_state(actual_total, strategy_volume)
    active = db.query(PositionMismatchIncident).filter_by(
        user_id=user_id, currency=currency, resolved_at=None).all()
    if state.status != "shortfall":
        for incident in active:
            incident.last_seen_at = current_time
            incident.resolved_at = current_time
        return None
    incident = next((row for row in active if row.mismatch_type == "shortfall"), None)
    if incident is None:
        incident = PositionMismatchIncident(
            user_id=user_id, currency=currency, mismatch_type="shortfall",
            actual_total=actual_total, strategy_volume=strategy_volume,
            difference=state.difference, detected_at=current_time, last_seen_at=current_time)
        db.add(incident)
    else:
        incident.actual_total = actual_total
        incident.strategy_volume = strategy_volume
        incident.difference = state.difference
        incident.last_seen_at = current_time
    return incident
