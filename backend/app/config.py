from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Datenbank
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "archiscribe"
    postgres_user: str = "postgres"
    postgres_password: str = ""

    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "qwen/qwen2.5-vl-72b-instruct"

    # Anwendung
    app_env: str = "development"
    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
