from types import SimpleNamespace

from signaltrade_portfolio import api_reporting


def test_reserved_amount_excludes_subscription_with_open_position(monkeypatch):
    rows = [
        {"id": 1, "enabled": True, "allocated_amount": 10_000},
        {"id": 2, "enabled": True, "allocated_amount": 10_000},
        {"id": 3, "enabled": False, "allocated_amount": 5_000},
    ]
    positions = {1: SimpleNamespace(volume=0.0001), 2: SimpleNamespace(volume=0)}
    monkeypatch.setattr(
        api_reporting,
        "load_strategy_position",
        lambda _db, subscription_id, _mode: positions[subscription_id],
    )

    assert api_reporting._reserved_amount(object(), 4, "live", rows) == 10_000
