import logging
import signal
import threading

from prometheus_client import start_http_server

from signaltrade_portfolio.config import settings

logger = logging.getLogger(__name__)


def run() -> None:
    logging.basicConfig(level=logging.INFO)
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    if settings.metrics_enabled:
        start_http_server(settings.portfolio_metrics_port)
    logger.info("Portfolio worker started: reconciliation interval=%s",
                settings.position_reconciliation_seconds)
    while not stop.wait(max(10, settings.position_reconciliation_seconds)):
        logger.info("Portfolio reconciliation cycle deferred until credential adapter is enabled")
