from datetime import datetime, timedelta

from signaltrade_portfolio.database import SessionLocal
from signaltrade_portfolio.incidents import record_currency_state
from signaltrade_portfolio.models import PositionMismatchIncident


def test_incident_is_updated_then_resolved_without_duplicates():
    first = datetime(2026, 1, 1)
    with SessionLocal() as db:
        record_currency_state(db, user_id=1, currency="BTC", actual_total=.4,
                              strategy_volume=1, now=first)
        db.commit()
        record_currency_state(db, user_id=1, currency="BTC", actual_total=.5,
                              strategy_volume=1, now=first + timedelta(minutes=1))
        db.commit()
        assert db.query(PositionMismatchIncident).count() == 1
        assert db.query(PositionMismatchIncident).one().difference == -.5
        record_currency_state(db, user_id=1, currency="BTC", actual_total=1,
                              strategy_volume=1, now=first + timedelta(minutes=2))
        db.commit()
        assert db.query(PositionMismatchIncident).one().resolved_at is not None
