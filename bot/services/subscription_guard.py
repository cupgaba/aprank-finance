import json
from dataclasses import dataclass
from typing import List, Optional

from ..database.models import BotSettings


@dataclass
class ChatSubscriptionConfig:
    chat_id: int
    channels: List[int]


class SubscriptionGuardService:
    @staticmethod
    def parse_settings(settings: BotSettings) -> List[ChatSubscriptionConfig]:
        raw = settings.market_chat_subscriptions
        if not raw:
            return []

        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return []

        result: List[ChatSubscriptionConfig] = []
        if not isinstance(data, list):
            return result

        for item in data:
            if not isinstance(item, dict):
                continue
            chat_id = item.get("chat_id")
            channels = item.get("channels", [])
            if chat_id is None:
                continue
            try:
                chat_id = int(chat_id)
            except (TypeError, ValueError):
                continue

            parsed_channels: List[int] = []
            if isinstance(channels, list):
                for channel in channels:
                    try:
                        parsed_channels.append(int(channel))
                    except (TypeError, ValueError):
                        continue

            result.append(ChatSubscriptionConfig(chat_id=chat_id, channels=parsed_channels))

        return result

    @staticmethod
    def serialize(configs: List[ChatSubscriptionConfig]) -> str:
        payload = [{"chat_id": c.chat_id, "channels": c.channels} for c in configs]
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def get_chat_config(settings: BotSettings, chat_id: int) -> Optional[ChatSubscriptionConfig]:
        for config in SubscriptionGuardService.parse_settings(settings):
            if config.chat_id == chat_id:
                return config
        return None
