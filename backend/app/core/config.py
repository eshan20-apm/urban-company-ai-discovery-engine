import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR.parent / "data"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    PROJECT_NAME: str = "Urban Company AI Opportunity & Discovery Engine"
    API_V1_PREFIX: str = "/api/v1"
    
    # Storage Paths
    BASE_DIR: Path = BASE_DIR
    DATA_RAW_DIR: Path = DATA_DIR / "raw"
    DATA_PROCESSED_DIR: Path = DATA_DIR / "processed"
    DATA_INVESTOR_DIR: Path = DATA_DIR / "investor_reports"
    DB_PATH: Path = BASE_DIR / "app" / "db" / "discovery_engine.db"
    
    # Gemini API Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    # Scraping Configuration
    GOOGLE_PLAY_APP_ID: str = "com.urbanclap.urbanclap"
    APPLE_APP_STORE_ID: str = "1032303419"
    DEFAULT_RATE_LIMIT_DELAY: float = 1.0

settings = Settings()
