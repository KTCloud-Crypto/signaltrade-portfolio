from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from signaltrade_portfolio.analytics import (
    AnalysisSourceTrade, AnalyzedTrade, analyze_trades, build_daily_pnl_points, build_metric,
)


def trade(identifier: int, action: str, price: float, volume: float, minutes: int = 0):
    return AnalysisSourceTrade(identifier, "KRW-BTC", action, price, volume, "success",
        datetime(2026, 1, 1)+timedelta(minutes=minutes), position_key=1)


def test_average_cost_realized_profit_and_fees():
    analyzed, excluded = analyze_trades([
        trade(1,"buy",100,2), trade(2,"buy",200,1,1), trade(3,"sell",250,2.5,2),
    ])
    metric=build_metric(analyzed)
    assert excluded == 0
    assert metric.realized_pnl == pytest.approx(291.1875)
    assert metric.total_fee == pytest.approx(0.5125)
    assert metric.win_rate == 100
    assert (metric.buy_amount,metric.sell_amount) == (400,625)


def test_failed_and_incomplete_trades_are_excluded():
    failed=trade(1,"buy",100,1)
    incomplete=AnalysisSourceTrade(2,"KRW-BTC","buy",100,None,"success",
        datetime(2026,1,1),position_key=1)
    analyzed,excluded=analyze_trades([replace(failed,status="failed"),incomplete])
    assert analyzed == []
    assert excluded == 2


def test_daily_pnl_accumulates_only_last_30_days():
    end=datetime(2026,2,1)
    rows=[AnalyzedTrade("KRW-BTC","sell",100,-120,.05,end-timedelta(days=2)),
          AnalyzedTrade("KRW-BTC","sell",100,20,.05,end)]
    points=build_daily_pnl_points(rows,end.date())
    assert len(points)==30
    assert points[-3].cumulative_pnl == -120
    assert points[-1].cumulative_pnl == -100
