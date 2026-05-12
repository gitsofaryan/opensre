from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.integrations._verification_adapters import _verify_whatsapp
from app.integrations.catalog import classify_integrations, resolve_effective_integrations
from app.integrations.config_models import WhatsAppIntegrationConfig
from app.integrations.store import get_integration, load_integrations, upsert_integration


def test_whatsapp_config_normalizes_url_and_phone_number() -> None:
    config = WhatsAppIntegrationConfig.model_validate(
        {
            "webhook_url": " https://bridge.example.com/hooks/incident/ ",
            "phone_number": " +15551234567 ",
        }
    )

    assert config.webhook_url == "https://bridge.example.com/hooks/incident"
    assert config.phone_number == "+15551234567"


def test_whatsapp_config_rejects_non_https_external_webhook() -> None:
    with pytest.raises(ValueError, match="WhatsApp webhook_url must use https"):
        WhatsAppIntegrationConfig.model_validate(
            {"webhook_url": "http://bridge.example.com/hooks/incident"}
        )


def test_whatsapp_config_allows_loopback_http_for_local_bridge() -> None:
    config = WhatsAppIntegrationConfig.model_validate(
        {"webhook_url": "http://localhost:8787/whatsapp"}
    )

    assert config.webhook_url == "http://localhost:8787/whatsapp"


def test_whatsapp_store_round_trip_and_effective_resolution(tmp_path: Path) -> None:
    store_file = tmp_path / "integrations.json"
    credentials = {
        "webhook_url": "https://bridge.example.com/hooks/incident",
        "phone_number": "+15551234567",
    }

    with patch("app.integrations.store.STORE_PATH", store_file):
        upsert_integration("whatsapp", {"credentials": credentials})

        stored = get_integration("whatsapp")
        assert stored is not None
        assert stored["credentials"] == credentials

        effective = resolve_effective_integrations(
            store_integrations=load_integrations(),
            env_integrations=[],
        )

    assert effective["whatsapp"]["source"] == "local store"
    assert effective["whatsapp"]["config"]["webhook_url"] == credentials["webhook_url"]
    assert effective["whatsapp"]["config"]["phone_number"] == credentials["phone_number"]


def test_whatsapp_classification_uses_normalized_runtime_config() -> None:
    resolved = classify_integrations(
        [
            {
                "id": "wa-prod",
                "service": "whatsapp",
                "status": "active",
                "credentials": {
                    "webhook_url": "https://bridge.example.com/hooks/incident/",
                    "phone_number": " +15551234567 ",
                },
            }
        ]
    )

    assert resolved["whatsapp"] == {
        "webhook_url": "https://bridge.example.com/hooks/incident",
        "phone_number": "+15551234567",
    }


def test_whatsapp_verifier_calls_provider_probe() -> None:
    with patch("app.notifications.providers.whatsapp.WhatsAppProvider.probe") as probe:
        probe.return_value = (True, "WhatsApp bridge connected successfully.")

        result = _verify_whatsapp(
            "local store",
            {
                "webhook_url": "https://bridge.example.com/hooks/incident",
                "phone_number": "+15551234567",
            },
        )

    assert result == {
        "service": "whatsapp",
        "source": "local store",
        "status": "passed",
        "detail": "WhatsApp bridge connected successfully.",
    }
    probe.assert_called_once_with(
        {
            "webhook_url": "https://bridge.example.com/hooks/incident",
            "phone_number": "+15551234567",
        }
    )


def test_whatsapp_verifier_reports_probe_failure() -> None:
    with patch("app.notifications.providers.whatsapp.WhatsAppProvider.probe") as probe:
        probe.return_value = (False, "Connectivity check failed: HTTP 401")

        result = _verify_whatsapp(
            "local store",
            {"webhook_url": "https://bridge.example.com/hooks/incident"},
        )

    assert result["status"] == "failed"
    assert result["detail"] == "Connectivity check failed: HTTP 401"


def test_whatsapp_verifier_rejects_invalid_config_without_probe() -> None:
    probe = MagicMock()

    with patch("app.notifications.providers.whatsapp.WhatsAppProvider.probe", probe):
        result = _verify_whatsapp(
            "local store",
            {"webhook_url": "http://bridge.example.com/hooks/incident"},
        )

    assert result["status"] == "missing"
    assert "WhatsApp webhook_url must use https" in result["detail"]
    probe.assert_not_called()
