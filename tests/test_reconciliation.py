import pytest

from signaltrade_portfolio.reconciliation import actual_coin_totals, calculate_reconciliation_state


def test_reconciliation_classifies_balance_states():
    assert calculate_reconciliation_state(1, 1).status == "matched"
    assert calculate_reconciliation_state(2, 1).status == "external_balance"
    state = calculate_reconciliation_state(.8, 1)
    assert state.status == "shortfall"
    assert state.shortfall_volume == pytest.approx(.2)


def test_locked_exchange_balance_is_included():
    assert actual_coin_totals([
        {"currency": "BTC", "balance": ".4", "locked": ".6"},
        {"currency": "KRW", "balance": "1000", "locked": "0"},
    ]) == {"BTC": 1.0}
