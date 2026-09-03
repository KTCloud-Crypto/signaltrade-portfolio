import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select

from signaltrade_portfolio.config import settings
from signaltrade_portfolio.database import get_db
from signaltrade_portfolio.models import strategy_table, supported_market_table, user_strategy_table
from signaltrade_portfolio.positions import load_strategy_position
from signaltrade_portfolio.identity_client import get_exchange_credentials
from signaltrade_portfolio.upbit_accounts import get_accounts


def require_internal_service_token(
    token: str | None = Header(default=None, alias="X-SignalTrade-Service-Token"),
):
    expected = settings.internal_service_token
    if not expected or not token or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="유효한 내부 서비스 토큰이 필요합니다.")


router = APIRouter(prefix="/internal/portfolio", tags=["Portfolio Internal"],
                   dependencies=[Depends(require_internal_service_token)])


@router.get("/users/{user_id}/open-positions")
def open_positions(user_id: int, db=Depends(get_db)) -> list[dict]:
    us, st, market = user_strategy_table, strategy_table, supported_market_table
    rows = db.execute(select(us.c.id, us.c.mode, st.c.id.label("strategy_id"),
        st.c.name.label("strategy_name"), st.c.code.label("strategy_code"),
        market.c.code.label("market")).select_from(
            us.join(st, st.c.id == us.c.strategy_id).join(market, market.c.id == us.c.market_id)
        ).where(us.c.user_id == user_id, us.c.enabled.is_(True), st.c.enabled.is_(True))).all()
    result = []
    for row in rows:
        position = load_strategy_position(db, row.id, row.mode)
        if position.volume > 0:
            result.append({"subscription_id": row.id, "strategy_id": row.strategy_id,
                "strategy_name": row.strategy_name, "strategy_code": row.strategy_code,
                "market": row.market, "mode": row.mode, "volume": position.volume,
                "average_buy_price": position.average_buy_price})
    return result


@router.get("/users/{user_id}/balance")
def user_balance(user_id: int) -> list[dict]:
    credentials = get_exchange_credentials(user_id)
    return get_accounts(access_key=credentials.access_key, secret_key=credentials.secret_key,
                        base_url=settings.upbit_api_base_url,
                        timeout=settings.upbit_api_timeout_seconds)
