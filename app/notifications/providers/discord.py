"""Discord notification provider implementation."""

from __future__ import annotations

import logging
from typing import Any

from app.notifications.interface import NotificationProvider
from app.notifications.models import NotificationEvent
from app.utils.discord_delivery import send_discord_report

logger = logging.getLogger(__name__)


class DiscordProvider(NotificationProvider):
    """Discord notification provider."""

    def send_notification(
        self,
        event: NotificationEvent,
        config: dict[str, Any],
    ) -> tuple[bool, str]:
        """Send an RCA report to Discord."""
        # Use the raw body to preserve Slack-style markdown which Discord partially supports,
        # rather than the plain-text fallback from format_text().
        return send_discord_report(event.body, config)

    def probe(self, config: dict[str, Any]) -> tuple[bool, str]:
        """Verify Discord connectivity."""
        from app.cli.wizard.integration_validators.http_probe_validators import validate_discord_bot

        bot_token = str(config.get("bot_token") or "")
        if not bot_token:
            return False, "Missing bot_token"

        result = validate_discord_bot(bot_token=bot_token)
        return result.ok, result.detail
