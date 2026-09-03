from datetime import datetime, timezone
from uuid import uuid4

from signaltrade_portfolio.models import MessageOutbox, PositionSyncAdjustment


def enqueue_position_reconciled(db, adjustment: PositionSyncAdjustment) -> MessageOutbox:
    db.flush()
    if adjustment.id is None:
        raise ValueError("PositionSyncAdjustment must be persisted before reconciliation event")
    key = f"position-adjustment:{adjustment.id}"
    message = MessageOutbox(
        message_id=str(uuid4()), message_type="PositionReconciled",
        correlation_id=key, producer="portfolio", schema_version=1,
        idempotency_key=key,
        payload={"adjustment_id": adjustment.id,
                 "user_strategy_id": adjustment.user_strategy_id},
        occurred_at=datetime.now(timezone.utc), status="pending", attempt_count=0)
    db.add(message)
    db.flush()
    return message
