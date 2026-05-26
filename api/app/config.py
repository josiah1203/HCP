from __future__ import annotations
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    hcp_provider: str = "onprem-compose"
    hcp_env: str = "dev"
    database_url: str = "postgresql+psycopg2://hcp:hcp@localhost:5432/hcp"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "dev-only-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 60
    jwt_refresh_expire_days: int = 30
    presigned_url_expiry_seconds: int = 900
    parse_queue_name: str = "hcp.parse"
    graph_queue_name: str = "hcp.graph"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "hcpsecret"
    opensearch_url: str = "http://localhost:9200"
    opensearch_index: str = "hcp-versions"
    rate_limit_per_minute: int = 1000


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
