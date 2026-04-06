# Authentication

All API requests are authenticated using API keys.

## API Keys

Keys are scoped to your account and carry full permissions. Keep them secret.

```
Authorization: Bearer sk_live_4xT9...
```

## Key Types

| Type | Prefix | Use |
|------|--------|-----|
| Live | `sk_live_` | Production requests |
| Test | `sk_test_` | Development and testing |

## Rotating Keys

POST /v1/api_keys/rotate

Invalidates the current key and returns a new one. Triggers a `api_key.rotated` **Webhook** event.

## Relationships

- Authentication is required by every **Endpoint**
- Key rotation triggers a **Webhook** event `api_key.rotated`
- **Customer** objects are scoped to the authenticated account
- **Charge**, **Subscription**, and **Invoice** objects inherit account scope from authentication

## Idempotency

Pass an `Idempotency-Key` header to safely retry requests. The key must be unique per logical operation and is valid for 24 hours.

```
Idempotency-Key: a8098c1a-f86e-11da-bd1a-00112444be1e
```

## Concepts

- **Idempotency** — safe retry mechanism using unique keys
- **Pagination** — all list endpoints are paginated
