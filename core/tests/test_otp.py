import json
import pytest
from django.test import Client
from unittest.mock import patch, MagicMock

client = Client()
@pytest.mark.django_db
@patch("core.views.Client")
def test_verify_otp_success(mock_twilio):

    session = client.session
    session["otp_phone"] = "+919999999999"
    session.save()

    # Create fake Twilio response
    mock_check = MagicMock()
    mock_check.status = "approved"

    mock_services = MagicMock()
    mock_services.verification_checks.create.return_value = mock_check

    mock_verify = MagicMock()
    mock_verify.services.return_value = mock_services

    mock_client = MagicMock()
    mock_client.verify.v2 = mock_verify

    mock_twilio.return_value = mock_client

    response = client.post(
        "/verify-otp/",
        data=json.dumps({"otp": "123456"}),
        content_type="application/json"
    )

    data = response.json()

    assert data["status"] == "verified"

@pytest.mark.django_db
@patch("core.views.Client")
def test_verify_otp_invalid(mock_twilio):

    session = client.session
    session["otp_phone"] = "+919999999999"
    session.save()

    # Fake Twilio response object
    mock_check = MagicMock()
    mock_check.status = "pending"

    # verification_checks.create()
    mock_verification_checks = MagicMock()
    mock_verification_checks.create.return_value = mock_check

    # services(...).verification_checks
    mock_service = MagicMock()
    mock_service.verification_checks = mock_verification_checks

    # verify.v2.services(...)
    mock_verify_v2 = MagicMock()
    mock_verify_v2.services.return_value = mock_service

    # client.verify.v2
    mock_client = MagicMock()
    mock_client.verify.v2 = mock_verify_v2

    mock_twilio.return_value = mock_client

    response = client.post(
        "/verify-otp/",
        data=json.dumps({"otp": "000000"}),
        content_type="application/json"
    )

    data = response.json()

    assert data["status"] == "invalid"