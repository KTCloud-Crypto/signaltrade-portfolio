import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from signaltrade_portfolio.config import settings


def get_prices(markets: list[str]) -> dict[str, float]:
    requested = sorted(set(markets))
    if not requested:
        return {}

    base_url = settings.upbit_api_base_url.rstrip('/')
    market_url = f"{base_url}/v1/market/all?{urlencode({'is_details': 'false'})}"
    with urlopen(Request(market_url, headers={"Accept": "application/json"}),
                 timeout=settings.upbit_api_timeout_seconds) as response:
        listed = {row["market"] for row in json.loads(response.read())}

    priceable = [market for market in requested if market in listed]
    if not priceable:
        return {}

    url = f"{base_url}/v1/ticker?{urlencode({'markets': ','.join(priceable)})}"
    with urlopen(Request(url, headers={"Accept": "application/json"}),
                 timeout=settings.upbit_api_timeout_seconds) as response:
        rows = json.loads(response.read())
    return {row["market"]: float(row["trade_price"]) for row in rows}
