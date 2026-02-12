from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Optional, Union


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Bot settings
    BOT_TOKEN: str

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/bot.db"

    # Admin settings
    ADMIN_IDS: list[int] = []  # List of admin telegram IDs

    # Channel settings
    CHANNEL_ID: Optional[int] = None  # Channel for publications
    LOG_CHANNEL_ID: Optional[int] = None  # Channel for logging changes

    # Reservation settings
    RESERVATION_HOURS: int = 24  # Default reservation time in hours

    # Scheduler settings
    SALES_REMINDER_HOUR: int = 23  # Hour to send sales reminder (23:00)
    SALES_REMINDER_MINUTE: int = 0
    PRICELIST_HOUR: int = 10  # Hour to publish daily pricelist
    PRICELIST_MINUTE: int = 0

    # Timezone
    TIMEZONE: str = "Asia/Yekaterinburg"

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: Union[str, list, int]) -> list[int]:
        if isinstance(v, list):
            return v
        if isinstance(v, int):
            return [v]
        if isinstance(v, str):
            if not v.strip():
                return []
            return [int(x.strip()) for x in v.split(",")]
        return []


settings = Settings()
