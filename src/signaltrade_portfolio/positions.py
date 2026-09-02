from signaltrade_portfolio.models import (
    PositionSyncAdjustment, strategy_execution_table, strategy_signal_table,
    strategy_table, user_strategy_table,
)
from signaltrade_portfolio.projection import CalculatedPosition, PositionEvent, project_position


def load_strategy_position(db, user_strategy_id: int, mode: str) -> CalculatedPosition:
    execution = strategy_execution_table
    signal = strategy_signal_table
    strategy = strategy_table
    subscription = user_strategy_table
    owner = db.execute(subscription.select().where(subscription.c.id == user_strategy_id)).first()
    if owner is None:
        return CalculatedPosition(0.0, 0.0, None)
    strategy_code = db.execute(strategy.select().where(
        strategy.c.id == owner.strategy_id)).first()
    if strategy_code is None or strategy_code.code == "manual_hold_v1":
        return CalculatedPosition(0.0, 0.0, None)
    statuses = {"simulated_success"} if mode == "simulated" else {"success", "partially_filled"}
    rows = db.execute(execution.select().where(
        execution.c.user_strategy_id == user_strategy_id,
        execution.c.mode == mode,
        execution.c.status.in_(statuses),
    )).all()
    events = []
    for row in rows:
        source = None
        if row.signal_id is not None:
            signal_row = db.execute(signal.select().where(signal.c.id == row.signal_id)).first()
            source = signal_row.source if signal_row else None
        if source == "external_sync" or not row.executed_volume:
            continue
        events.append(PositionEvent(f"execution_{row.action}", row.executed_volume,
                                    row.average_price or row.price, row.created_at, row.id,
                                    row.paid_fee))
    if mode == "live":
        adjustments = db.query(PositionSyncAdjustment).filter_by(
            user_strategy_id=user_strategy_id).all()
        events.extend(PositionEvent("deduct", row.volume, None, row.created_at,
                                    1_000_000_000 + row.id)
                      for row in adjustments if row.action in {"deduct", "sell"})
    return project_position(events)
