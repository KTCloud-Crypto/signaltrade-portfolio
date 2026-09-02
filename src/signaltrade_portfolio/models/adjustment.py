from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, Float, Integer, String

from signaltrade_portfolio.database import Base


class PositionSyncAdjustment(Base):
    __tablename__ = "position_sync_adjustment"
    __table_args__ = (CheckConstraint("volume > 0",
                                     name="ck_position_sync_adjustment_volume_positive"),)
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    user_strategy_id = Column(Integer, nullable=False, index=True)
    strategy_execution_id = Column(Integer, nullable=True, unique=True)
    currency = Column(String(16), nullable=False)
    action = Column(String(8), nullable=False)
    volume = Column(Float, nullable=False)
    reference_price = Column(Float, nullable=False)
    cost_basis_source = Column(String(32), nullable=False)
    difference_before = Column(Float, nullable=False)
    source = Column(String(16), nullable=False)
    reason = Column(String(255))
    idempotency_key = Column(String(64), unique=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
