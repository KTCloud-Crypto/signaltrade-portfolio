from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String

from signaltrade_portfolio.database import Base


class PositionMismatchIncident(Base):
    __tablename__ = "position_mismatch_incident"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    currency = Column(String(16), nullable=False, index=True)
    mismatch_type = Column(String(32), nullable=False, index=True)
    actual_total = Column(Float, nullable=False)
    strategy_volume = Column(Float, nullable=False)
    difference = Column(Float, nullable=False)
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    notified_at = Column(DateTime)
    resolved_at = Column(DateTime, index=True)
