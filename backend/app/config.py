from pathlib import Path
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
    openrouter_timeout: int = 120  # Timeout in Sekunden
    openrouter_max_retries: int = 3  # Maximale Retry-Versuche

    # Datei-Management
    files_base_path: str = "./files"
    max_file_size_mb: int = 50  # Maximale PDF-Größe in MB
    test_tenant_id: str = "00000000-0000-0000-0000-000000000001"

    # Processing
    max_concurrent_processing: int = 3  # Maximale parallele PDF-Verarbeitungen

    # Anwendung
    app_env: str = "development"
    log_level: str = "INFO"

    # API-Auth
    dev_api_key: str = "sk-tenant-00000000-0000-0000-0000-000000000001-a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"

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

    @property
    def files_path(self) -> Path:
        """Basis-Pfad für alle Datei-Operationen."""
        return Path(self.files_base_path).resolve()

    @property
    def inbox_path(self) -> Path:
        """Pfad für eingehende PDFs (Watchdog überwacht diesen Ordner)."""
        return self.files_path / "inbox"

    @property
    def processing_path(self) -> Path:
        """Temporärer Arbeitsbereich für laufende Verarbeitungen."""
        return self.files_path / "processing"

    @property
    def archive_path(self) -> Path:
        """Dauerhafte Ablage für verarbeitete Dateien."""
        return self.files_path / "archive"

    @property
    def error_path(self) -> Path:
        """Ablage für fehlgeschlagene Verarbeitungen."""
        return self.files_path / "error"

    @property
    def max_file_size_bytes(self) -> int:
        """Maximale Dateigröße in Bytes."""
        return self.max_file_size_mb * 1024 * 1024


settings = Settings()
