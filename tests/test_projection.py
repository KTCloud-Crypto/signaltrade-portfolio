from datetime import datetime, timedelta

from signaltrade_portfolio.projection import PositionEvent, project_position


def test_projection_uses_average_cost_and_sell_reduces_position():
    now = datetime.utcnow()
    position = project_position([
        PositionEvent("execution_buy", 1, 100, now, 1),
        PositionEvent("execution_buy", 1, 200, now + timedelta(seconds=1), 2),
        PositionEvent("execution_sell", .5, 250, now + timedelta(seconds=2), 3),
    ])
    assert position.volume == 1.5
    assert position.cost_basis == 225
    assert position.average_buy_price == 150
