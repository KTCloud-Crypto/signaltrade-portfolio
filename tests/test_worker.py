from sqlalchemy import insert

from signaltrade_portfolio.database import SessionLocal
from signaltrade_portfolio.identity_client import ExchangeCredentials
from signaltrade_portfolio.models import PositionMismatchIncident, user_strategy_table, user_table
from signaltrade_portfolio.worker import monitor_positions_once, monitor_positions_safely


def test_worker_persists_shortfall_incident(monkeypatch):
    with SessionLocal() as db:
        db.execute(insert(user_table), [{"id": 1}])
        db.execute(insert(user_strategy_table), [{"id": 10, "user_id": 1,
            "strategy_id": 20, "market_id": 30, "mode": "live", "enabled": True}])
        db.commit()
    monkeypatch.setattr("signaltrade_portfolio.worker.get_exchange_credentials",
                        lambda user_id: ExchangeCredentials(access_key="a", secret_key="s"))

    monkeypatch.setattr("signaltrade_portfolio.worker.get_accounts", lambda **kwargs: [
        {"currency": "BTC", "balance": "0.4", "locked": "0"}
    ])
    monkeypatch.setattr("signaltrade_portfolio.worker.recorded_strategy_volumes",
                        lambda db, user_id: {"BTC": 1.0})
    assert monitor_positions_once() == (1, 1)
    with SessionLocal() as db:
        incident = db.query(PositionMismatchIncident).one()
        assert incident.currency == "BTC"
        assert incident.difference == -0.6
        assert incident.resolved_at is None


def test_worker_retries_after_cycle_level_failure(monkeypatch, caplog):
    def fail_cycle():
        raise RuntimeError("database unavailable")

    monkeypatch.setattr("signaltrade_portfolio.worker.monitor_positions_once", fail_cycle)

    assert monitor_positions_safely() is None
    assert "retrying next interval" in caplog.text
