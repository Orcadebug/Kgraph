# Webhook Signatures

NiaPay signs all webhook payloads so you can verify they originated from us.

## Signature Header

Every webhook request includes a `NiaPay-Signature` header:

```
NiaPay-Signature: t=1712345678,v1=abc123def456...
```

- `t` — Unix timestamp of the request
- `v1` — HMAC-SHA256 signature of `t.payload` using your webhook secret

## Verifying Signatures

```python
import hmac, hashlib, time

def verify_signature(payload: bytes, header: str, secret: str, tolerance: int = 300) -> bool:
    parts = dict(item.split("=", 1) for item in header.split(","))
    timestamp = int(parts["t"])
    
    if abs(time.time() - timestamp) > tolerance:
        return False  # Replay attack protection
    
    signed_payload = f"{timestamp}.{payload.decode()}"
    expected = hmac.new(
        secret.encode(), signed_payload.encode(), hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, parts["v1"])
```

## Relationships

- Signature verification is required for all **Webhook** event processing
- The webhook secret is per-endpoint and different from your **Authentication** API key
- Failing signature verification should return HTTP 400 to NiaPay
- NiaPay retries failed deliveries (non-2xx response) with exponential backoff

## Replay Protection

The timestamp `t` is checked against your server time. Requests older than `tolerance` seconds (default 300) are rejected. This prevents replay attacks.

## Endpoint Registration

Register webhook endpoints via the Dashboard or the API. Each endpoint can subscribe to specific **Webhook** event types.
