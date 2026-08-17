from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str 
    database_url_sync: str 
    db_pool_size: int = 10 
    db_max_overflow: int = 20
    db_echo: bool = False

@lru_cache
def get_db_settings() -> DatabaseSettings:
    return DatabaseSettings()

db_settings = get_db_settings