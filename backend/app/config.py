from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO / ".env", extra="ignore")
    database_url: str = f"sqlite:///{REPO / '.data' / 'agent.sqlite'}"
    demo_mode: bool = True
    display_timezone: str = "Europe/Berlin"
    admin_token: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_starttls: bool = True
    openai_api_key: str = ""
    openrouter_api_key: str = ""
    openrouter_site_url: str = "http://localhost:8000"
    openrouter_app_name: str = "Fieldwork Executive Job Agent"
    llm_provider: str = "openrouter"
    llm_model: str = ""
    llm_input_price: float = 0
    llm_output_price: float = 0

    @property
    def model_key(self) -> str:
        return self.openrouter_api_key if self.llm_provider == "openrouter" else self.openai_api_key

    @property
    def model_configured(self) -> bool:
        return bool(
            self.model_key
            and self.llm_model
            and min(self.llm_input_price, self.llm_output_price) > 0
        )


settings = Settings()
