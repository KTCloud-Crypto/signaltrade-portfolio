from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Table

from signaltrade_portfolio.database import Base

user_table = Table("user", Base.metadata, Column("id", Integer, primary_key=True))
strategy_table = Table("strategy", Base.metadata, Column("id", Integer, primary_key=True),
    Column("code", String(100), nullable=False), Column("name", String(100), nullable=False),
    Column("timeframe_minutes", Integer, nullable=False, default=10), Column("default_invest_ratio", Float, nullable=False, default=0.2),
    Column("enabled", Boolean, nullable=False))
supported_market_table = Table("supported_market", Base.metadata,
    Column("id", Integer, primary_key=True), Column("code", String(20), nullable=False),
    Column("display_name", String(50), nullable=False, default=""), Column("enabled", Boolean, nullable=False, default=True),
    Column("sort_order", Integer, nullable=False, default=0))
user_strategy_table = Table("user_strategy", Base.metadata,
    Column("id", Integer, primary_key=True), Column("user_id", Integer, nullable=False),
    Column("strategy_id", Integer, nullable=False), Column("market_id", Integer, nullable=False),
    Column("mode", String(16), nullable=False), Column("enabled", Boolean, nullable=False),
    Column("invest_ratio", Float, nullable=False, default=0.2), Column("allocated_amount", Float),
    Column("allocation_mode", String(16), nullable=False, default="ratio"), Column("timeframe_minutes", Integer, nullable=False, default=10))
strategy_signal_table = Table("strategy_signal", Base.metadata,
    Column("id", Integer, primary_key=True), Column("source", String(16), nullable=False))
strategy_execution_table = Table("strategy_execution", Base.metadata,
    Column("id", Integer, primary_key=True), Column("signal_id", Integer),
    Column("user_strategy_id", Integer, nullable=False), Column("mode", String(16), nullable=False),
    Column("action", String(8), nullable=False), Column("status", String(20), nullable=False),
    Column("price", Float, nullable=False), Column("order_volume", Float), Column("executed_volume", Float),
    Column("average_price", Float), Column("paid_fee", Float),
    Column("created_at", DateTime, nullable=False))
api_key_table = Table("api_key", Base.metadata,
    Column("id", Integer, primary_key=True), Column("user_id", Integer, nullable=False))
