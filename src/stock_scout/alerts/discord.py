from __future__ import annotations

from stock_scout.config import Settings


def send_discord_message(settings: Settings, text: str) -> None:
    """
    Sends message to Discord via webhook URL.
    Requires extras: `pip install -e ".[alerts]"`.
    """
    _require_httpx()
    import httpx

    if not settings.discord_webhook_url:
        raise RuntimeError("Discord not configured (STOCK_SCOUT_DISCORD_WEBHOOK_URL)")

    payload = {"content": text}
    r = httpx.post(settings.discord_webhook_url, json=payload, timeout=20)
    r.raise_for_status()


def _require_httpx() -> None:
    try:
        import httpx  # noqa: F401
    except Exception as e:  # pragma: no cover
        raise RuntimeError('Missing alerts dependencies. Install with: pip install -e ".[alerts]"') from e

