"""WhatsApp e2e-equivalent investigation publish flow.

This test uses the real integration classifier and publish_findings node, and
mocks only the outbound network POST to the WhatsApp bridge.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.integrations.catalog import classify_integrations


def _make_state(resolved_integrations: dict[str, Any]) -> dict[str, Any]:
    return {
        "problem_md": "Checkout API error rate is above threshold.",
        "root_cause": "Database connection pool exhausted after deploy.",
        "root_cause_category": "database",
        "remediation_steps": [
            "Increase pool size for checkout-api.",
            "Roll back the deploy if saturation continues.",
        ],
        "slack_context": {},
        "resolved_integrations": resolved_integrations,
        "available_sources": {},
    }


def _patch_publish_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.nodes.publish_findings.node.build_report_context",
        lambda _state: {},
    )
    monkeypatch.setattr(
        "app.nodes.publish_findings.node.format_slack_message",
        lambda _ctx: (
            "### RCA Finding\n\n"
            "Root cause: Database connection pool exhausted after deploy.\n\n"
            "Remediation: Increase pool size for checkout-api."
        ),
    )
    monkeypatch.setattr(
        "app.nodes.publish_findings.node.build_slack_blocks",
        lambda _ctx: [],
    )
    monkeypatch.setattr(
        "app.nodes.publish_findings.node.create_investigation_and_attach_url",
        lambda _state, _message, _summary: (
            "inv-whatsapp-123",
            "https://app.tracer.cloud/investigations/inv-whatsapp-123",
        ),
    )
    monkeypatch.setattr(
        "app.nodes.publish_findings.node.render_report",
        lambda _message, **_kwargs: None,
    )
    monkeypatch.setattr(
        "app.nodes.publish_findings.node.open_in_editor",
        lambda _message: None,
    )


def test_investigation_publish_flow_sends_whatsapp_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolved = classify_integrations(
        [
            {
                "id": "whatsapp-oncall",
                "service": "whatsapp",
                "status": "active",
                "credentials": {
                    "webhook_url": "https://bridge.example.com/whatsapp/incidents",
                    "phone_number": "+15551234567",
                },
            }
        ]
    )
    assert "whatsapp" in resolved
    _patch_publish_dependencies(monkeypatch)

    captured_posts: list[dict[str, Any]] = []

    def _fake_post_json(**kwargs: Any) -> SimpleNamespace:
        captured_posts.append(kwargs)
        return SimpleNamespace(ok=True, status_code=200, error="", text="ok")

    monkeypatch.setattr("app.notifications.providers.whatsapp.post_json", _fake_post_json)
    mock_send_slack = MagicMock(return_value=(False, None))
    mock_build_action_blocks = MagicMock(return_value=[])

    with (
        patch("app.utils.slack_delivery.send_slack_report", mock_send_slack),
        patch("app.utils.slack_delivery.build_action_blocks", mock_build_action_blocks),
    ):
        from app.nodes.publish_findings.node import generate_report

        result = generate_report(_make_state(resolved))  # type: ignore[arg-type]

    assert result["report"].startswith("### RCA Finding")
    assert len(captured_posts) == 1

    post = captured_posts[0]
    assert post["url"] == "https://bridge.example.com/whatsapp/incidents"
    assert post["timeout"] == 15.0

    payload = post["payload"]
    assert payload["phone"] == "+15551234567"
    assert "Investigation findings for inv-whatsapp-123" in payload["text"]
    assert "Database connection pool exhausted after deploy" in payload["text"]
    assert (
        "View details: https://app.tracer.cloud/investigations/inv-whatsapp-123" in payload["text"]
    )
