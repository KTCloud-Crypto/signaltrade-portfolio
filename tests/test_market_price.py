import json

from signaltrade_portfolio import market_price


class _Response:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return json.dumps(self.value).encode()


def test_get_prices_excludes_delisted_markets_but_prices_listed_assets(monkeypatch):
    requested_urls = []

    def fake_urlopen(request, timeout):
        requested_urls.append(request.full_url)
        if "/v1/market/all" in request.full_url:
            return _Response([{"market": "KRW-BTC"}, {"market": "KRW-USDT"}])
        return _Response([{"market": "KRW-USDT", "trade_price": 1380}])

    monkeypatch.setattr(market_price, "urlopen", fake_urlopen)

    assert market_price.get_prices(["KRW-USDT", "KRW-DELISTED"]) == {"KRW-USDT": 1380.0}
    assert "KRW-USDT" in requested_urls[1]
    assert "KRW-DELISTED" not in requested_urls[1]
