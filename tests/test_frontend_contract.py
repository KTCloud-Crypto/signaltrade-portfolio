from signaltrade_portfolio import api_reporting
from signaltrade_portfolio.identity_client import ExchangeCredentialsUnavailable
from signaltrade_portfolio.main import app


def test_frontend_reporting_routes_and_dashboard_contract():
    spec = app.openapi()
    for method, path in [("get", "/strategies/positions"), ("get", "/positions/dashboard"),
                         ("get", "/positions/summary"), ("get", "/analytics"),
                         ("post", "/positions/reconciliation/deduct")]:
        assert method in spec["paths"].get(path, {})
    assert set(spec["components"]["schemas"]["PositionsDashboardOut"]["properties"]) == {
        "balances", "reconciliation", "portfolio", "account"}
    assert set(spec["components"]["schemas"]["LiveAccountSummaryOut"]["properties"]) == {
        "purchase_amount", "evaluation_amount", "realized_profit_loss",
        "unrealized_profit_loss", "profit_loss", "return_rate"}
    assert set(spec["components"]["schemas"]["AnalyticsOut"]["properties"]) == {
        "all_time", "today", "week", "month", "daily_pnl", "tickers",
        "excluded_trade_count", "fee_included"}


def test_dashboard_uses_empty_accounts_when_exchange_key_is_not_registered(monkeypatch):
    def unavailable(_user_id: int):
        raise ExchangeCredentialsUnavailable("API Key가 없습니다.")

    monkeypatch.setattr(api_reporting, "_accounts", unavailable)

    assert api_reporting._dashboard_accounts(1) == []


def test_dashboard_attempts_to_price_every_krw_asset():
    accounts = [
        {"currency": "KRW"},
        {"currency": "ETH"},
        {"currency": "PURSE"},
        {"currency": "XRP"},
        {"currency": "ETH"},
    ]

    assert api_reporting._price_markets(accounts) == [
        "KRW-ETH", "KRW-PURSE", "KRW-XRP",
    ]
