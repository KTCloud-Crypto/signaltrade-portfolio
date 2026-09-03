from sqlalchemy import insert

from signaltrade_portfolio.database import SessionLocal
from signaltrade_portfolio.identity_client import ExchangeCredentials
from signaltrade_portfolio.models import user_strategy_table, user_table
from signaltrade_portfolio.worker import monitor_positions_once


def test_worker_checks_each_live_user_once_without_writes(monkeypatch):
    with SessionLocal() as db:
        db.execute(insert(user_table), [{"id": 1}])
        db.execute(insert(user_strategy_table), [{"id": 10, "user_id": 1,
            "strategy_id": 20, "market_id": 30, "mode": "live", "enabled": True}])
        db.commit()
    monkeypatch.setattr("signaltrade_portfolio.worker.get_exchange_credentials",
                        lambda user_id: ExchangeCredentials(access_key="a", secret_key="s"))

    monkeypatch.setattr("signaltrade_portfolio.worker.get_accounts", lambda **kwargs: [
        {"currency": "KRW", "balance": "1000", "locked": "0"}
    ])
    monkeypatch.setattr("signaltrade_portfolio.worker.recorded_strategy_volumes",
                        lambda db, user_id: {})
    assert monitor_positions_once() == (1, 0)
