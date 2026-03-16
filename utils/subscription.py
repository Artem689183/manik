from __future__ import annotations

from urllib.parse import urlparse

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError


def _channel_username_from_link(channel_link: str | None) -> str | None:
    if not channel_link:
        return None

    link = channel_link.strip()
    if not link:
        return None

    if link.startswith("@"):
        return link

    parsed = urlparse(link if "://" in link else f"https://{link}")
    host = parsed.netloc.lower()
    if host not in {"t.me", "telegram.me", "www.t.me", "www.telegram.me"}:
        return None

    slug = parsed.path.strip("/").split("/")[0]
    if not slug or slug.startswith("+"):
        return None
    return f"@{slug}"


async def is_user_subscribed(
    bot: Bot, user_id: int, channel_id: int, channel_link: str | None = None
) -> bool:
    targets: list[int | str] = [channel_id]
    username = _channel_username_from_link(channel_link)
    if username:
        targets.append(username)

    verification_unavailable = False

    for chat_id in targets:
        try:
            member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        except (TelegramBadRequest, TelegramForbiddenError) as error:
            error_text = str(error).lower()
            if (
                "member list is inaccessible" in error_text
                or "chat admin required" in error_text
                or "not enough rights" in error_text
            ):
                # Telegram does not allow subscription verification in this chat.
                verification_unavailable = True
            continue

        if member.status in {
            ChatMemberStatus.CREATOR,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.RESTRICTED,
        }:
            return True

    # Do not block booking when Telegram API denies member list access.
    return verification_unavailable
