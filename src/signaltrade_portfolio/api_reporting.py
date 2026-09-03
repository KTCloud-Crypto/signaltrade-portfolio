from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text

from signaltrade_portfolio.database import get_db
from signaltrade_portfolio.identity_client import AuthenticatedUser, get_current_user
from signaltrade_portfolio.market_price import get_prices
from signaltrade_portfolio.models import strategy_table, supported_market_table, user_strategy_table
from signaltrade_portfolio.positions import load_strategy_position
from signaltrade_portfolio.reconciliation import (
    actual_coin_totals, calculate_reconciliation_state, recorded_strategy_positions,
    recorded_strategy_volumes,
)
from signaltrade_portfolio.schemas import (
    AnalyticsMetric, AnalyticsOut, DailyPnlPoint, ExchangeAccountStatusOut, ExchangeAssetOut,
    LiveAccountSummaryOut, PortfolioAllocationOut, PortfolioSummaryOut,
    PositionReconciliationOut, PositionsDashboardOut, ReconciliationStrategyOut,
    StrategyPositionOut, TickerPerformance, UpbitBalanceOut,
)
from signaltrade_portfolio.api_reconciliation import _accounts

position_router = APIRouter(prefix="/positions", tags=["Portfolio"])
strategy_router = APIRouter(prefix="/strategies", tags=["Portfolio"])
analytics_router = APIRouter(prefix="/analytics", tags=["Analytics"])
KST = timezone(timedelta(hours=9))


def _strategy_rows(db, user_id: int, mode: str):
    us, strategy, market = user_strategy_table, strategy_table, supported_market_table
    return db.execute(select(us, strategy.c.code.label("strategy_code"),
        strategy.c.name.label("strategy_name"), strategy.c.id.label("strategy_id"),
        market.c.code.label("market"), market.c.display_name.label("market_name"),
        strategy.c.timeframe_minutes.label("default_timeframe"),
        strategy.c.default_invest_ratio.label("default_ratio")).select_from(
        us.join(strategy, strategy.c.id == us.c.strategy_id).join(market, market.c.id == us.c.market_id)
    ).where(us.c.user_id == user_id, us.c.mode == mode,
            strategy.c.code != "manual_hold_v1")).mappings().all()


def _reconciliation(accounts, db, user_id: int) -> list[PositionReconciliationOut]:
    actual_rows = {row["currency"]: row for row in accounts if row["currency"] != "KRW"}
    actual = actual_coin_totals(accounts); recorded = recorded_strategy_volumes(db, user_id)
    positions = recorded_strategy_positions(db, user_id); result = []
    for currency in sorted(set(actual) | set(recorded)):
        account = actual_rows.get(currency, {})
        available, locked = float(account.get("balance", 0)), float(account.get("locked", 0))
        state = calculate_reconciliation_state(available + locked, recorded.get(currency, 0))
        message = {"matched": "실제 잔고와 전략 기록이 일치합니다.",
                   "external_balance": "전략에 귀속되지 않은 외부 자산이 있습니다.",
                   "shortfall": "실제 잔고가 전략 기록보다 부족합니다."}[state.status]
        result.append(PositionReconciliationOut(currency=currency, actual_available=available,
            actual_locked=locked, actual_total=state.actual_total, strategy_volume=state.strategy_volume,
            difference=state.difference, status=state.status, message=message,
            strategies=[ReconciliationStrategyOut(strategy_id=p["strategy_id"],
                subscription_id=p["subscription_id"], strategy_name=p["strategy_name"],
                market=p["market"], volume=p["volume"]) for p in positions
                if p["market"].endswith(f"-{currency}")]))
    return result


def _portfolio(accounts, db, user_id: int, prices: dict[str, float]) -> PortfolioSummaryOut:
    available = sum(float(row["balance"]) for row in accounts if row["currency"] == "KRW")
    allocations, managed = [], 0.0
    for row in _strategy_rows(db, user_id, "live"):
        position = load_strategy_position(db, row["id"], "live")
        value = position.volume * prices.get(row["market"], 0)
        managed += value
        allocations.append(PortfolioAllocationOut(strategy_id=row["strategy_id"],
            strategy_name=row["strategy_name"], strategy_code=row["strategy_code"], market=row["market"],
            invest_ratio=row["invest_ratio"], allocation_amount=row["allocated_amount"] or 0,
            allocation_mode=row["allocation_mode"], current_position_value=value, enabled=row["enabled"]))
    return PortfolioSummaryOut(available_krw=available, managed_positions_value=managed,
                               total_equity=available + managed, strategies=allocations)


@position_router.get("/dashboard", response_model=PositionsDashboardOut)
def dashboard(db=Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    accounts = _accounts(user.id)
    markets = [f"KRW-{row['currency']}" for row in accounts if row["currency"] != "KRW"]
    prices = get_prices(markets)
    balances = [UpbitBalanceOut(currency=row["currency"], balance=float(row["balance"]),
        locked=float(row["locked"]), avg_buy_price=float(row["avg_buy_price"])) for row in accounts
        if float(row["balance"]) + float(row["locked"]) > 0]
    reconciliation = _reconciliation(accounts, db, user.id)
    portfolio = _portfolio(accounts, db, user.id, prices)
    recorded = recorded_strategy_volumes(db, user.id)
    supported = {row.code for row in db.execute(select(supported_market_table.c.code).where(
        supported_market_table.c.enabled.is_(True))).all()}
    assets=[]; coin_value=managed=unallocated_value=0.0
    for row in accounts:
        if row["currency"] == "KRW" or float(row["balance"]) + float(row["locked"]) <= 0: continue
        currency=row["currency"]; market=f"KRW-{currency}"; total=float(row["balance"])+float(row["locked"])
        state=calculate_reconciliation_state(total, recorded.get(currency, 0)); price=prices.get(market)
        evaluation=total*price if price is not None else None
        coin_value += evaluation or 0; managed += state.strategy_volume*(price or 0)
        unallocated_value += state.unallocated_volume*(price or 0)
        assets.append(ExchangeAssetOut(currency=currency, market=market if market in supported else None,
            supported=market in supported, available=float(row["balance"]), locked=float(row["locked"]),
            total=total, average_buy_price=float(row["avg_buy_price"]), current_price=price,
            evaluation_amount=evaluation, strategy_volume=state.strategy_volume,
            unallocated_volume=state.unallocated_volume,
            unallocated_value=state.unallocated_volume*price if price is not None else None,
            shortfall_volume=state.shortfall_volume, reconciliation_status=state.status,
            strategies=next((r.strategies for r in reconciliation if r.currency == currency), [])))
    krw=next((row for row in accounts if row["currency"] == "KRW"), None)
    available=float(krw["balance"]) if krw else 0; locked=float(krw["locked"]) if krw else 0
    reserved=sum((row["allocated_amount"] or 0) for row in _strategy_rows(db,user.id,"live") if row["enabled"])
    account=ExchangeAccountStatusOut(available_krw=available, strategy_reserved_krw=reserved,
        strategy_available_krw=max(0, available-reserved), locked_krw=locked, total_krw=available+locked,
        coin_evaluation_amount=coin_value, account_equity=available+locked+coin_value,
        managed_positions_value=managed, managed_equity=available+managed,
        unallocated_value=unallocated_value, assets=assets)
    return PositionsDashboardOut(balances=balances,reconciliation=reconciliation,portfolio=portfolio,account=account)


@position_router.get("/summary", response_model=LiveAccountSummaryOut)
def summary(db=Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    rows=_strategy_rows(db,user.id,"live"); prices=get_prices(list({row["market"] for row in rows}))
    purchase=evaluation=0.0
    for row in rows:
        pos=load_strategy_position(db,row["id"],"live"); purchase+=pos.cost_basis
        evaluation+=pos.volume*prices.get(row["market"],0)
    unrealized=evaluation-purchase
    return LiveAccountSummaryOut(purchase_amount=purchase,evaluation_amount=evaluation,
        realized_profit_loss=0,unrealized_profit_loss=unrealized,profit_loss=unrealized,
        return_rate=unrealized/purchase*100 if purchase else None)


@strategy_router.get("/positions", response_model=list[StrategyPositionOut])
def positions(mode: Literal["simulated","live"] = Query("simulated"), market: str = Query("KRW-BTC"),
              all_markets: bool = Query(False), db=Depends(get_db),
              user: AuthenticatedUser = Depends(get_current_user)):
    rows=_strategy_rows(db,user.id,mode); result=[]
    for row in rows:
        if not all_markets and row["market"] != market.upper(): continue
        live=load_strategy_position(db,row["id"],"live"); paper=load_strategy_position(db,row["id"],"simulated")
        selected=paper if mode=="simulated" else live
        if all_markets and selected.volume <= 0: continue
        result.append(StrategyPositionOut(strategy_id=row["strategy_id"],strategy_name=row["strategy_name"],
            strategy_code=row["strategy_code"],market=row["market"],enabled=row["enabled"],
            timeframe_minutes=row["timeframe_minutes"],invest_ratio=row["invest_ratio"],
            volume=live.volume,average_buy_price=live.average_buy_price,
            status="holding" if live.volume>0 else "flat",paper_volume=paper.volume,
            paper_average_buy_price=paper.average_buy_price,
            paper_status="holding" if paper.volume>0 else "flat"))
    return result


def _metric(rows):
    sells=[r for r in rows if r["action"]=="sell"]
    buy=sum(float((r["average_price"] or r["price"])*(r["executed_volume"] or r["order_volume"] or 0)) for r in rows if r["action"]=="buy")
    sell=sum(float((r["average_price"] or r["price"])*(r["executed_volume"] or r["order_volume"] or 0)) for r in sells)
    fees=sum(float(r["paid_fee"] or 0) for r in rows)
    return AnalyticsMetric(realized_pnl=0,total_fee=round(fees,4),trade_count=len(rows),sell_count=len(sells),
        win_count=0,win_rate=0,buy_amount=round(buy,4),sell_amount=round(sell,4))


@analytics_router.get("", response_model=AnalyticsOut)
def analytics(mode: Literal["live","simulated"] = Query("live"), db=Depends(get_db),
              user: AuthenticatedUser = Depends(get_current_user)):
    rows=db.execute(text("""SELECT e.* FROM strategy_execution e JOIN user_strategy us ON us.id=e.user_strategy_id
        JOIN strategy s ON s.id=us.strategy_id LEFT JOIN strategy_signal ss ON ss.id=e.signal_id
        WHERE e.user_id=:uid AND e.mode=:mode AND s.code<>'manual_hold_v1'
        AND COALESCE(ss.source,'')<>'external_sync' ORDER BY e.created_at"""),{"uid":user.id,"mode":mode}).mappings().all()
    valid=[r for r in rows if (r["status"] in ({"simulated_success"} if mode=="simulated" else {"success","partially_filled"}))
           and (r["executed_volume"] or r["order_volume"])]
    now=datetime.utcnow(); today=now.astimezone(KST).date()
    points=[DailyPnlPoint(date=today-timedelta(days=i),pnl=0,cumulative_pnl=0) for i in range(29,-1,-1)]
    metric=_metric(valid); empty=_metric([])
    grouped=defaultdict(list)
    for row in valid: grouped[row["market"]].append(row)
    total=sum(m.buy_amount for m in [_metric(v) for v in grouped.values()])
    tickers=[]
    for ticker,items in grouped.items():
        m=_metric(items); tickers.append(TickerPerformance(ticker=ticker,buy_amount=m.buy_amount,
            sell_amount=m.sell_amount,realized_pnl=0,trade_count=m.trade_count,
            weight=m.buy_amount/total*100 if total else 0))
    return AnalyticsOut(all_time=metric,today=empty,week=empty,month=empty,daily_pnl=points,
        tickers=tickers,excluded_trade_count=len(rows)-len(valid),fee_included=True)
