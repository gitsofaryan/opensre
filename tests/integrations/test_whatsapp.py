from unittest.mock import patch

import pytest

from app.notifications.models import NotificationEvent
from app.notifications.providers.whatsapp import WhatsAppProvider


@pytest.fixture
def whatsapp_provider():
    return WhatsAppProvider()


@pytest.fixture
def sample_event():
    return NotificationEvent(
        title="High CPU on Production",
        body="CPU reached 99% on node-1",
        severity="critical",
        investigation_id="inv-123",
    )


@patch("app.notifications.providers.whatsapp.post_json")
def test_whatsapp_send_notification_success(mock_post, whatsapp_provider, sample_event):
    mock_post.return_value.status_code = 200
    mock_post.return_value.ok = True

    config = {
        "webhook_url": "https://api.whatsapp.bridge/v1/abcd-1234",
        "phone_number": "+1234567890",
    }

    success, error = whatsapp_provider.send_notification(sample_event, config)

    assert success is True
    assert error == ""
    assert mock_post.called

    kwargs = mock_post.call_args.kwargs
    assert kwargs["url"] == "https://api.whatsapp.bridge/v1/abcd-1234"

    payload = kwargs["payload"]
    assert "High CPU on Production" in payload["text"]
    assert payload["phone"] == "+1234567890"


@patch("app.notifications.providers.whatsapp.post_json")
def test_whatsapp_send_notification_failure(mock_post, whatsapp_provider, sample_event):
    mock_post.return_value.status_code = 500
    mock_post.return_value.ok = False
    mock_post.return_value.error = "Internal Server Error"

    config = {"webhook_url": "https://api.whatsapp.bridge/v1/abcd-1234"}

    success, error = whatsapp_provider.send_notification(sample_event, config)

    assert success is False
    assert "Internal Server Error" in error


@patch("app.notifications.providers.whatsapp.post_json")
def test_whatsapp_probe_success(mock_post, whatsapp_provider):
    mock_post.return_value.status_code = 200
    mock_post.return_value.ok = True

    config = {"webhook_url": "https://api.whatsapp.bridge/v1/abcd-1234"}

    success, detail = whatsapp_provider.probe(config)

    assert success is True
    assert "connected successfully" in detail


@patch("app.notifications.providers.whatsapp.post_json")
def test_whatsapp_probe_failure(mock_post, whatsapp_provider):
    mock_post.return_value.status_code = 401
    mock_post.return_value.ok = False
    mock_post.return_value.error = "Unauthorized"

    config = {"webhook_url": "https://api.whatsapp.bridge/v1/abcd-1234"}

    success, detail = whatsapp_provider.probe(config)

    assert success is False
    assert "Unauthorized" in detail
