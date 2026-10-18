from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


class Settings(BaseSettings):
    """App settings, read from environment variables (prefix RH_) or .env.
    # local default
    RH_DATABASE_URL=sqlite:///data/registerhelper.db
    # postgresql server
    RH_DATABASE_URL=postgresql+psycopg://user:pass@host/db   # server
    """

    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_prefix="RH_")

    database_url: str = f"sqlite:///{DATA_DIR / 'registerhelper.db'}"
    data_dir: Path = DATA_DIR


settings = Settings()
