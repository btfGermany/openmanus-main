"""
Configuration for OpenManus API service.

Handles API-specific configuration separate from the agent config.
"""

import os
import tomllib
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field


def get_api_root() -> Path:
    """Get the API root directory."""
    return Path(__file__).resolve().parent.parent


class ApiLLMSettings(BaseModel):
    """API layer LLM settings for overrides."""

    model: str = Field(default="gpt-4o", description="Default model")
    api_key: Optional[str] = Field(default=None, description="Optional override")


class RedisSettings(BaseModel):
    """Redis connection settings."""

    url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL"
    )


class DatabaseSettings(BaseModel):
    """Database settings."""

    url: str = Field(
        default="sqlite:///data/api_keys.db",
        description="Database connection URL"
    )


class StorageSettings(BaseModel):
    """Storage settings for task workspaces."""

    base_path: Path = Field(
        default=Path("/app/workspace/tasks"),
        description="Base path for task workspaces"
    )
    log_path: Path = Field(
        default=Path("/app/api_logs"),
        description="Path for API logs"
    )
    cleanup_days: int = Field(
        default=7,
        description="Days to retain task workspaces before cleanup"
    )


class RateLimitSettings(BaseModel):
    """Rate limiting settings."""

    enabled: bool = Field(default=True, description="Enable rate limiting")
    window_seconds: int = Field(default=60, description="Rate limit window in seconds")


class WorkerSettings(BaseModel):
    """Worker settings."""

    concurrency: int = Field(default=5, description="Max concurrent workers")
    timeout_default: int = Field(default=300, description="Default task timeout")
    cleanup_on_shutdown: bool = Field(default=True, description="Cleanup on worker shutdown")


class ApiKeySettings(BaseModel):
    """API key management settings."""

    admin_key: Optional[str] = Field(
        default=None,
        description="Admin API key for management endpoints"
    )
    key_prefix: str = Field(
        default="sk-manus-",
        description="Prefix for generated API keys"
    )
    default_rate_limit_rpm: int = Field(default=60, description="Default requests per minute")
    default_rate_limit_rph: int = Field(default=1000, description="Default requests per hour")
    default_concurrent_tasks: int = Field(default=3, description="Default max concurrent tasks")


class ApiConfig(BaseModel):
    """API configuration."""

    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8000, description="API port")
    debug: bool = Field(default=False, description="Debug mode")
    workers: int = Field(default=1, description="Number of API workers")
    title: str = Field(default="OpenManus API", description="API title")
    version: str = Field(default="1.0.0", description="API version")
    description: Optional[str] = Field(
        default="Production AI Agent API Service",
        description="API description"
    )


class Config:
    """Singleton API configuration."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        """Load configuration from environment and files."""
        # Load from config file if exists
        config_path = get_api_root() / "api" / "config.toml"
        
        if config_path.exists():
            with config_path.open("rb") as f:
                raw_config = tomllib.load(f)
        else:
            raw_config = {}

        # Build config
        api_section = raw_config.get("api", {})
        redis_section = raw_config.get("redis", {})
        db_section = raw_config.get("database", {})
        storage_section = raw_config.get("storage", {})
        rate_limit_section = raw_config.get("rate_limit", {})
        worker_section = raw_config.get("worker", {})
        apikey_section = raw_config.get("apikey", {})

        self.api = ApiConfig(
            host=os.getenv("API_HOST", api_section.get("host", "0.0.0.0")),
            port=int(os.getenv("API_PORT", api_section.get("port", 8000))),
            debug=os.getenv("API_DEBUG", "").lower() == "true" or api_section.get("debug", False),
            workers=int(os.getenv("API_WORKERS", api_section.get("workers", 1))),
            title=api_section.get("title", "OpenManus API"),
            version=api_section.get("version", "1.0.0"),
            description=api_section.get("description", "Production AI Agent API Service"),
        )

        self.redis = RedisSettings(
            url=os.getenv("REDIS_URL", redis_section.get("url", "redis://localhost:6379")),
        )

        self.database = DatabaseSettings(
            url=os.getenv("DATABASE_URL", db_section.get("url", "sqlite:///data/api_keys.db")),
        )

        root_path = get_api_root()
        self.storage = StorageSettings(
            base_path=Path(os.getenv("STORAGE_PATH", storage_section.get("base_path", str(root_path / "workspace" / "tasks")))),
            log_path=Path(os.getenv("LOG_PATH", storage_section.get("log_path", str(root_path / "api_logs")))),
            cleanup_days=storage_section.get("cleanup_days", 7),
        )

        self.rate_limit = RateLimitSettings(
            enabled=rate_limit_section.get("enabled", True),
            window_seconds=rate_limit_section.get("window_seconds", 60),
        )

        self.worker = WorkerSettings(
            concurrency=int(os.getenv("WORKER_CONCURRENCY", worker_section.get("concurrency", 5))),
            timeout_default=int(os.getenv("WORKER_TIMEOUT", worker_section.get("timeout_default", 300))),
            cleanup_on_shutdown=worker_section.get("cleanup_on_shutdown", True),
        )

        self.apikey = ApiKeySettings(
            admin_key=os.getenv("ADMIN_API_KEY", apikey_section.get("admin_key")),
            key_prefix=apikey_section.get("key_prefix", "sk-manus-"),
            default_rate_limit_rpm=apikey_section.get("default_rate_limit_rpm", 60),
            default_rate_limit_rph=apikey_section.get("default_rate_limit_rph", 1000),
            default_concurrent_tasks=apikey_section.get("default_concurrent_tasks", 3),
        )

    def get_llm_config(self) -> ApiLLMSettings:
        """Get API layer LLM config (for any API-specific overrides)."""
        return ApiLLMSettings(
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            api_key=os.getenv("LLM_API_KEY"),
        )


api_config = Config()