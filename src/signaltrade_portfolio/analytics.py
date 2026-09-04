from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from signaltrade_portfolio.projection import PositionEvent, project_ledger
from signaltrade_portfolio.schemas import AnalyticsMetric, DailyPnlPoint

KST = timezone(timedelta(hours=9))


@dataclass(frozen=True, slots=True)
class AnalysisSourceTrade:
    id: int
    ticker: str
    action: str
    price: float | None
    volume: float | None
    status: str
    created_at: datetime
    position_key: int
    paid_fee: float | None = None
    event_type: str = "trade"


@dataclass(frozen=True, slots=True)
class AnalyzedTrade:
    ticker: str
    action: str
    amount: float
    pnl: float
    fee: float
    created_at: datetime


def kst_date(value: datetime) -> date:
    utc_value = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    return utc_value.astimezone(KST).date()


def utc_start_of_kst_day(day: date) -> datetime:
    return datetime.combine(day, datetime.min.time(), tzinfo=KST).astimezone(
        timezone.utc
    ).replace(tzinfo=None)


def analyze_trades(source: list[AnalysisSourceTrade]) -> tuple[list[AnalyzedTrade], int]:
    grouped: dict[int, list[PositionEvent]] = defaultdict(list)
    valid: list[AnalysisSourceTrade] = []
    excluded = 0
    for item in sorted(source, key=lambda row: (row.created_at, row.id)):
        if item.status != "success" or not item.price or not item.volume or item.volume <= 0:
            excluded += 1
            continue
        if item.event_type == "deduct":
            kind = "deduct"
        elif item.action in {"buy", "sell"}:
            kind = f"execution_{item.action}"
        else:
            excluded += 1
            continue
        grouped[item.position_key].append(PositionEvent(
            kind, item.volume, item.price, item.created_at, item.id, item.paid_fee
        ))
        valid.append(item)

    details = {}
    for events in grouped.values():
        details.update(project_ledger(events, include_buy_fees_in_cost=True).events)
    analyzed = []
    for item in valid:
        if item.event_type == "deduct":
            continue
        detail = details.get(item.id)
        if detail is None:
            continue
        analyzed.append(AnalyzedTrade(
            item.ticker, item.action, detail.transaction_amount,
            detail.realized_profit_loss or 0.0, detail.fee, item.created_at,
        ))
    return analyzed, excluded


def build_metric(trades: list[AnalyzedTrade], start: datetime | None = None) -> AnalyticsMetric:
    selected = [row for row in trades if start is None or row.created_at >= start]
    buys = [row for row in selected if row.action == "buy"]
    sells = [row for row in selected if row.action == "sell"]
    wins = sum(row.pnl > 0 for row in sells)
    return AnalyticsMetric(
        realized_pnl=round(sum(row.pnl for row in sells), 4),
        total_fee=round(sum(row.fee for row in selected), 4),
        trade_count=len(selected), sell_count=len(sells), win_count=wins,
        win_rate=round(wins / len(sells) * 100, 2) if sells else 0,
        buy_amount=round(sum(row.amount for row in buys), 4),
        sell_amount=round(sum(row.amount for row in sells), 4),
    )


def build_daily_pnl_points(trades: list[AnalyzedTrade], end_date: date) -> list[DailyPnlPoint]:
    by_date: dict[date, float] = defaultdict(float)
    for row in trades:
        if row.action == "sell":
            by_date[kst_date(row.created_at)] += row.pnl
    cumulative = 0.0
    result = []
    for offset in range(29, -1, -1):
        day = end_date - timedelta(days=offset)
        pnl = by_date.get(day, 0.0)
        cumulative += pnl
        result.append(DailyPnlPoint(
            date=day, pnl=round(pnl, 4), cumulative_pnl=round(cumulative, 4)
        ))
    return result
