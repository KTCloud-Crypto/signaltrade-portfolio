import httpx
from pydantic import BaseModel

from signaltrade_portfolio.config import settings


class ExchangeCredentials(BaseModel):
    access_key: str
    secret_key: str


class ExchangeCredentialsUnavailable(RuntimeError):
    pass


def get_exchange_credentials(user_id: int) -> ExchangeCredentials:
    if not settings.internal_service_token:
        raise ExchangeCredentialsUnavailable("내부 서비스 토큰이 설정되지 않았습니다.")
    try:
        response = httpx.get(
            f"{settings.identity_service_url}/internal/exchange-credentials/{user_id}",
            headers={"X-SignalTrade-Service-Token": settings.internal_service_token},
            timeout=settings.identity_service_timeout_seconds,
        )
    except httpx.HTTPError as error:
        raise ExchangeCredentialsUnavailable("Identity 자격증명을 조회할 수 없습니다.") from error
    if response.status_code != 200:
        raise ExchangeCredentialsUnavailable("Identity 자격증명을 조회할 수 없습니다.")
    return ExchangeCredentials.model_validate(response.json())
