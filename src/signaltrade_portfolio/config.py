from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)
    environment: str = "development"
    database_url: str = "postgresql://signaltrade:signaltrade-local@localhost:5432/signaltrade"
    internal_service_token: str = ""
    position_reconciliation_seconds: int = 60
    metrics_enabled: bool = True
    portfolio_metrics_port: int = 9103


settings = Settings()
