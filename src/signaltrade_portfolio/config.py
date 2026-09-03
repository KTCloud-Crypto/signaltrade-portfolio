from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)
    environment: str = "development"
    database_url: str = "postgresql://signaltrade:signaltrade-local@localhost:5432/signaltrade"
    internal_service_token: str = ""
    identity_service_url: str = "http://identity-api:8000"
    identity_service_timeout_seconds: float = 5.0
    upbit_api_base_url: str = "https://api.upbit.com"
    upbit_api_timeout_seconds: float = 5.0
    position_reconciliation_seconds: int = 60
    metrics_enabled: bool = True
    portfolio_metrics_port: int = 9103


settings = Settings()
