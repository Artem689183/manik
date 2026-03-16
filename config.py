import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    bot_token: str
    admin_id: int
    channel_id: int
    channel_link: str
    db_path: str = "database/bot.db"
    timezone: str = "Asia/Yekaterinburg"


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    admin_id = int(os.getenv("ADMIN_ID", "0"))
    channel_id = int(os.getenv("CHANNEL_ID", "0"))
    channel_link = os.getenv("CHANNEL_LINK", "").strip()
    db_path = os.getenv("DB_PATH", "database/bot.db").strip()
    timezone = os.getenv("TIMEZONE", "Asia/Yekaterinburg").strip()

    if not token:
        raise ValueError("BOT_TOKEN не задан. Добавьте его в .env")
    if admin_id == 0:
        raise ValueError("ADMIN_ID не задан. Добавьте его в .env")
    if channel_id == 0:
        raise ValueError("CHANNEL_ID не задан. Добавьте его в .env")
    if not channel_link:
        raise ValueError("CHANNEL_LINK не задан. Добавьте его в .env")

    return Settings(
        bot_token=token,
        admin_id=admin_id,
        channel_id=channel_id,
        channel_link=channel_link,
        db_path=db_path,
        timezone=timezone,
    )
