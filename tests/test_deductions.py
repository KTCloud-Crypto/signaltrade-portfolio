from signaltrade_portfolio.database import SessionLocal
from signaltrade_portfolio.deductions import apply_position_deduction
from signaltrade_portfolio.models import MessageOutbox, PositionSyncAdjustment


def test_deduction_and_position_reconciled_are_atomic(monkeypatch):
    monkeypatch.setattr("signaltrade_portfolio.deductions.recorded_strategy_positions",
                        lambda db, user_id: [{"subscription_id": 7, "market": "KRW-BTC",
                                             "volume": 1.0, "average_buy_price": 100.0}])
    monkeypatch.setattr("signaltrade_portfolio.deductions.recorded_strategy_volumes",
                        lambda db, user_id: {"BTC": 1.0})
    accounts = [{"currency": "BTC", "balance": "0.4", "locked": "0"}]
    with SessionLocal() as db:
        adjustment = apply_position_deduction(
            db, user_id=1, accounts=accounts, subscription_id=7, volume=.6,
            source="web", idempotency_key="request-item-1")
        db.commit()
        assert adjustment.action == "deduct"
        outbox = db.query(MessageOutbox).one()
        assert outbox.message_type == "PositionReconciled"
        assert outbox.payload == {"adjustment_id": adjustment.id, "user_strategy_id": 7}
        assert outbox.idempotency_key == f"position-adjustment:{adjustment.id}"
        assert db.query(PositionSyncAdjustment).count() == 1
