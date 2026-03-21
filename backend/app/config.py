from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./poetry.db"

    # OpenRouter LLM
    openrouter_api_key: str = ""
    llm_model: str = "google/gemini-2.0-flash"


settings = Settings()
