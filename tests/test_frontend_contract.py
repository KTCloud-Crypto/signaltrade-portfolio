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
