import logging
import signal
import threading

import pyupbit
from prometheus_client import start_http_server
from sqlalchemy import distinct, select

from signaltrade_portfolio.config import settings
from signaltrade_portfolio.database import SessionLocal
from signaltrade_portfolio.identity_client import get_exchange_credentials
from signaltrade_portfolio.models import user_strategy_table
from signaltrade_portfolio.reconciliation import (
    actual_coin_totals, calculate_reconciliation_state, recorded_strategy_volumes,
)

logger = logging.getLogger(__name__)


def monitor_positions_once() -> tuple[int, int]:
    checked = 0
    shortfalls = 0
    with SessionLocal() as db:
        user_ids = db.execute(select(distinct(user_strategy_table.c.user_id)).where(
            user_strategy_table.c.mode == "live")).scalars().all()
        for user_id in user_ids:
            try:
                credentials = get_exchange_credentials(user_id)
                accounts = pyupbit.Upbit(credentials.access_key,
                                         credentials.secret_key).get_balances()
                if not isinstance(accounts, list):
                    raise ValueError("invalid Upbit balance response")
                actual = actual_coin_totals(accounts)
                recorded = recorded_strategy_volumes(db, user_id)
                for currency in set(actual) | set(recorded):
                    state = calculate_reconciliation_state(
                        actual.get(currency, 0.0), recorded.get(currency, 0.0))
                    if state.status == "shortfall":
                        shortfalls += 1
                        logger.warning("Portfolio shortfall: user_id=%s currency=%s difference=%s",
                                       user_id, currency, state.difference)
                checked += 1
            except Exception as error:
                db.rollback()
                logger.warning("Portfolio reconciliation failed: user_id=%s error=%s",
                               user_id, type(error).__name__)
    return checked, shortfalls


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    if settings.metrics_enabled:
        start_http_server(settings.portfolio_metrics_port)
    logger.info("Portfolio worker started: reconciliation interval=%s",
                settings.position_reconciliation_seconds)
    while not stop.is_set():
        checked, shortfalls = monitor_positions_once()
        logger.info("Portfolio reconciliation cycle: checked=%s shortfalls=%s",
                    checked, shortfalls)
        stop.wait(max(10, settings.position_reconciliation_seconds))
