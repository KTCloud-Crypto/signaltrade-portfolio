from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from signaltrade_portfolio.config import settings

options = ({"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
           if settings.database_url.startswith("sqlite") else {"pool_pre_ping": True})
engine = create_engine(settings.database_url, **options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
