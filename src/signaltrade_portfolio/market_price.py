import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from signaltrade_portfolio.config import settings


def get_prices(markets: list[str]) -> dict[str, float]:
    if not markets:
        return {}
    url = f"{settings.upbit_api_base_url.rstrip('/')}/v1/ticker?{urlencode({'markets': ','.join(markets)})}"
    with urlopen(Request(url, headers={"Accept": "application/json"}),
                 timeout=settings.upbit_api_timeout_seconds) as response:
        rows = json.loads(response.read())
    return {row["market"]: float(row["trade_price"]) for row in rows}
