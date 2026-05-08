from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./ecommerce.db"
    SECRET_KEY: str = "supersecretkey-change-in-production-32chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    APP_NAME: str = "ShopCLI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    class Config:
        env_file = Path(__file__).parent.parent / ".env"
        extra = "ignore"

settings = Settings()
