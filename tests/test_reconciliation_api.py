from fastapi.testclient import TestClient
from sqlalchemy import insert

from signaltrade_portfolio.database import SessionLocal
from signaltrade_portfolio.identity_client import AuthenticatedUser, get_current_user
from signaltrade_portfolio.main import app
from signaltrade_portfolio.models import MessageOutbox, PositionSyncAdjustment, user_table


def _user() -> AuthenticatedUser:
    return AuthenticatedUser(id=1, username="portfolio-user", nickname="Portfolio",
                             bot_enabled=False, execution_mode="live",
                             live_trading_enabled=True)


def test_deduction_api_requires_bearer_token():
    response = TestClient(app).post("/positions/reconciliation/deduct", json={
        "currency": "BTC", "expected_difference": -.6,
        "deductions": [{"subscription_id": 7, "volume": .6}],
    })
    assert response.status_code == 401


def test_user_selected_deduction_creates_adjustment_and_outbox(monkeypatch):
    with SessionLocal() as db:
        db.execute(insert(user_table), [{"id": 1}])
        db.commit()
    positions = [{"subscription_id": 7, "market": "KRW-BTC", "strategy_name": "S",
                  "strategy_code": "s", "volume": 1.0, "average_buy_price": 100.0}]
    monkeypatch.setattr("signaltrade_portfolio.api_reconciliation._accounts", lambda user_id: [
        {"currency": "BTC", "balance": ".4", "locked": "0"}])
    monkeypatch.setattr("signaltrade_portfolio.api_reconciliation.recorded_strategy_positions",
                        lambda db, user_id: positions)
    monkeypatch.setattr("signaltrade_portfolio.api_reconciliation.recorded_strategy_volumes",
                        lambda db, user_id: {"BTC": 1.0})
    monkeypatch.setattr("signaltrade_portfolio.deductions.recorded_strategy_positions",
                        lambda db, user_id: positions)
    monkeypatch.setattr("signaltrade_portfolio.deductions.recorded_strategy_volumes",
                        lambda db, user_id: {"BTC": 1.0})
    app.dependency_overrides[get_current_user] = _user
    try:
        response = TestClient(app).post("/positions/reconciliation/deduct", json={
            "currency": "btc", "expected_difference": -.6,
            "deductions": [{"subscription_id": 7, "volume": .6}],
            "idempotency_key": "browser-request-1",
        })
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 204
    with SessionLocal() as db:
        assert db.query(PositionSyncAdjustment).count() == 1
        assert db.query(MessageOutbox).filter_by(message_type="PositionReconciled").count() == 1
