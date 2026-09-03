from fastapi import FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from signaltrade_portfolio.api_internal import router
from signaltrade_portfolio.api_reconciliation import router as reconciliation_router
from signaltrade_portfolio.database import SessionLocal

app = FastAPI(title="SignalTrade Portfolio API", version="1.0.0")
app.include_router(router)
app.include_router(reconciliation_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        raise HTTPException(status_code=503, detail="database unavailable") from error
    return {"status": "ready"}
