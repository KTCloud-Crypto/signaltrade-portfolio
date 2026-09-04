from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import insert

from signaltrade_portfolio.config import settings
from signaltrade_portfolio.database import SessionLocal
from signaltrade_portfolio.main import app
from signaltrade_portfolio.models import (
    paper_account_table, strategy_execution_table, strategy_signal_table, strategy_table,
    supported_market_table, user_strategy_table, user_table,
)


def test_internal_open_positions_is_protected_and_projects_trading_ledger(monkeypatch):
    monkeypatch.setattr(settings, "internal_service_token", "runtime-token")
    with SessionLocal() as db:
        db.execute(insert(user_table), [{"id": 1}])
        db.execute(insert(strategy_table), [{"id": 10, "code": "sma", "name": "SMA",
                                             "enabled": True}])
        db.execute(insert(supported_market_table), [{"id": 20, "code": "KRW-BTC"}])
        db.execute(insert(user_strategy_table), [{"id": 30, "user_id": 1,
            "strategy_id": 10, "market_id": 20, "mode": "simulated", "enabled": True}])
        db.execute(insert(strategy_signal_table), [{"id": 40, "source": "engine"}])
        db.execute(insert(strategy_execution_table), [{"id": 50, "signal_id": 40,
            "user_strategy_id": 30, "mode": "simulated", "action": "buy",
            "status": "simulated_success", "price": 50000, "executed_volume": .2,
            "average_price": 50000, "paid_fee": 5, "created_at": datetime.utcnow()}])
        db.commit()
    client = TestClient(app)
    assert client.get("/internal/portfolio/users/1/open-positions").status_code == 401
    response = client.get("/internal/portfolio/users/1/open-positions",
        headers={"X-SignalTrade-Service-Token": "runtime-token"})
    assert response.status_code == 200
    assert response.json()[0]["subscription_id"] == 30
    assert response.json()[0]["volume"] == .2

    market_response = client.get("/internal/portfolio/markets/krw-btc/open-positions",
        headers={"X-SignalTrade-Service-Token": "runtime-token"})
    assert market_response.status_code == 200
    assert market_response.json() == [{
        "subscription_id": 30,
        "user_id": 1,
        "mode": "simulated",
        "volume": .2,
        "average_buy_price": 50000.0,
    }]


def test_internal_reconciliation_state_returns_balance_difference(monkeypatch):
    monkeypatch.setattr(settings, "internal_service_token", "runtime-token")
    monkeypatch.setattr(
        "signaltrade_portfolio.api_internal.user_balance",
        lambda _user_id: [{"currency": "BTC", "balance": "0.3", "locked": "0.0"}],
    )
    monkeypatch.setattr(
        "signaltrade_portfolio.api_internal.recorded_strategy_volumes",
        lambda _db, _user_id: {"BTC": 0.2},
    )
    response = TestClient(app).get(
        "/internal/portfolio/users/1/reconciliation-state",
        headers={"X-SignalTrade-Service-Token": "runtime-token"},
    )
    assert response.status_code == 200
    assert response.json()["BTC"] == {
        "actual_total": 0.3,
        "strategy_volume": 0.2,
        "difference": 0.09999999999999998,
    }


def test_internal_strategy_cash_deducts_unspent_reservations(monkeypatch):
    monkeypatch.setattr(settings, "internal_service_token", "runtime-token")
    with SessionLocal() as db:
        db.execute(insert(user_table), [{"id": 1}])
        db.execute(insert(paper_account_table), [{"id": 1, "user_id": 1, "cash_balance": 100_000}])
        db.execute(insert(strategy_table), [{"id": 10, "code": "sma", "name": "SMA", "enabled": True}])
        db.execute(insert(supported_market_table), [{"id": 20, "code": "KRW-BTC"}])
        db.execute(insert(user_strategy_table), [{"id": 30, "user_id": 1,
            "strategy_id": 10, "market_id": 20, "mode": "simulated", "enabled": True,
            "allocated_amount": 40_000}])
        db.commit()
    response = TestClient(app).get(
        "/internal/portfolio/users/1/strategy-cash?mode=simulated",
        headers={"X-SignalTrade-Service-Token": "runtime-token"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "cash_balance": 100_000.0,
        "reserved_amount": 40_000.0,
        "available_cash": 59_970.0,
    }
