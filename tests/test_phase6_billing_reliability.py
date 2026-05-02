import hashlib
import hmac
import json

from app.api import billing


def test_paystack_signature_verification_accepts_valid_hash():
    secret = "sk_test_abc123"
    payload = {"event": "charge.success", "data": {"id": 123, "reference": "ref_1"}}
    raw = json.dumps(payload).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), raw, hashlib.sha512).hexdigest()

    assert billing._verify_paystack_signature(raw, sig, secret) is True


def test_paystack_signature_verification_rejects_invalid_hash():
    secret = "sk_test_abc123"
    raw = b'{"event":"charge.success"}'
    assert billing._verify_paystack_signature(raw, "bad-signature", secret) is False


def test_extract_provider_event_id_uses_data_id_when_present():
    event_id = billing._extract_provider_event_id("charge.success", {"id": 999, "reference": "abc"})
    assert event_id == "charge.success:999"


def test_extract_provider_event_id_falls_back_to_reference():
    event_id = billing._extract_provider_event_id("charge.success", {"reference": "abc"})
    assert event_id == "charge.success:abc"


def test_extract_metadata_handles_json_string():
    data = {"metadata": '{"user_id": 42, "tier": "pro"}'}
    metadata = billing._extract_metadata(data)
    assert metadata["user_id"] == 42
    assert metadata["tier"] == "pro"

