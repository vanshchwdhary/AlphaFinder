from __future__ import annotations

from dataclasses import dataclass

from stock_scout.config import Settings


def send_telegram_message(settings: Settings, text: str) -> None:
    """
    Sends message to Telegram chat via bot token.
    Requires extras: `pip install -e ".[alerts]"`.
    """
    _require_httpx()
    import httpx

    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        raise RuntimeError("Telegram not configured (STOCK_SCOUT_TELEGRAM_BOT_TOKEN / STOCK_SCOUT_TELEGRAM_CHAT_ID)")

    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {"chat_id": settings.telegram_chat_id, "text": text, "disable_web_page_preview": True}
    r = httpx.post(url, json=payload, timeout=20)
    r.raise_for_status()


def _require_httpx() -> None:
    try:
        import httpx  # noqa: F401
    except Exception as e:  # pragma: no cover
        raise RuntimeError('Missing alerts dependencies. Install with: pip install -e ".[alerts]"') from e

