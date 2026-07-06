from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_planner_model: str = "anthropic/claude-sonnet-4-6"
    llm_default_model: str = "anthropic/claude-sonnet-4-6"
    llm_timeout_seconds: int = 120
    llm_max_retries: int = 3
    database_url: str = "sqlite+aiosqlite:///./data/smart_reporting.db"
    storage_type: str = "local"
    local_storage_path: str = "./data/files"
    upload_max_size_mb: int = 50
    workopilot_base_url: str = "https://agent.workopilot.com/net-api"
    workopilot_api_key: str = ""
    server_port: int = 8080
    jwt_secret: str = ""
    jwt_expire_days: int = 7
    redis_url: str = "redis://localhost:6379/0"
    testing: bool = False
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3001"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
