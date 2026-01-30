from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
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
    TIMEZONE: str = "Europe/Moscow"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str):
            if field_name == "ADMIN_IDS":
                if not raw_val:
                    return []
                return [int(x.strip()) for x in raw_val.split(",")]
            return raw_val


settings = Settings()
