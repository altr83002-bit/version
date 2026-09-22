import os


def owner_ids() -> list[int]:
    raw = os.getenv("OWNER_IDS", "")
    return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]


def check_permission(user_id: int, guild_owner_id: int | None = None) -> bool:
    ids = owner_ids()
    return user_id in ids or user_id == guild_owner_id


def locked_channel() -> str:
    return os.getenv("LOCKED_CHANNEL_ID", "").strip()


def channel_allowed(channel_id: int) -> bool:
    lc = locked_channel()
    if not lc:
        return True
    return str(channel_id) == lc
