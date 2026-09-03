from datetime import date
from typing import Literal
from pydantic import BaseModel

class UpbitBalanceOut(BaseModel):
    currency: str; balance: float; locked: float; avg_buy_price: float
class ReconciliationStrategyOut(BaseModel):
    strategy_id: int; subscription_id: int; strategy_name: str; market: str; volume: float
class PositionReconciliationOut(BaseModel):
    currency: str; actual_available: float; actual_locked: float; actual_total: float
    strategy_volume: float; difference: float; status: str; message: str
    strategies: list[ReconciliationStrategyOut]
class PortfolioAllocationOut(BaseModel):
    strategy_id: int; strategy_name: str; strategy_code: str; market: str; invest_ratio: float
    allocation_amount: float; allocation_mode: Literal["ratio", "amount"] = "ratio"
    current_position_value: float; enabled: bool
class PortfolioSummaryOut(BaseModel):
    available_krw: float; managed_positions_value: float; total_equity: float
    strategies: list[PortfolioAllocationOut]
class ExchangeAssetOut(BaseModel):
    currency: str; market: str | None; supported: bool; available: float; locked: float; total: float
    average_buy_price: float; current_price: float | None; evaluation_amount: float | None
    strategy_volume: float; unallocated_volume: float; unallocated_value: float | None
    shortfall_volume: float; reconciliation_status: str; strategies: list[ReconciliationStrategyOut]
class ExchangeAccountStatusOut(BaseModel):
    available_krw: float; strategy_reserved_krw: float; strategy_available_krw: float
    locked_krw: float; total_krw: float; coin_evaluation_amount: float; account_equity: float
    managed_positions_value: float; managed_equity: float; unallocated_value: float
    assets: list[ExchangeAssetOut]
class PositionsDashboardOut(BaseModel):
    balances: list[UpbitBalanceOut]; reconciliation: list[PositionReconciliationOut]
    portfolio: PortfolioSummaryOut; account: ExchangeAccountStatusOut
class LiveAccountSummaryOut(BaseModel):
    purchase_amount: float; evaluation_amount: float; realized_profit_loss: float
    unrealized_profit_loss: float; profit_loss: float; return_rate: float | None
class StrategyPositionOut(BaseModel):
    strategy_id: int; strategy_name: str; strategy_code: str; market: str; enabled: bool
    timeframe_minutes: int; invest_ratio: float; volume: float; average_buy_price: float | None
    status: Literal["holding", "flat"]; paper_volume: float; paper_average_buy_price: float | None
    paper_status: Literal["holding", "flat"]
class AnalyticsMetric(BaseModel):
    realized_pnl: float; total_fee: float; trade_count: int; sell_count: int; win_count: int
    win_rate: float; buy_amount: float; sell_amount: float
class DailyPnlPoint(BaseModel):
    date: date; pnl: float; cumulative_pnl: float
class TickerPerformance(BaseModel):
    ticker: str; buy_amount: float; sell_amount: float; realized_pnl: float; trade_count: int; weight: float
class AnalyticsOut(BaseModel):
    all_time: AnalyticsMetric; today: AnalyticsMetric; week: AnalyticsMetric; month: AnalyticsMetric
    daily_pnl: list[DailyPnlPoint]; tickers: list[TickerPerformance]; excluded_trade_count: int
    fee_included: bool = False
