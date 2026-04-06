# Errors

All API errors follow a consistent structure.

## Error Object

```json
{
  "error": {
    "type": "card_error",
    "code": "card_declined",
    "message": "Your card was declined.",
    "param": "payment_method",
    "charge": "ch_1abc23"
  }
}
```

## Error Types

| Type | HTTP Status | Description |
|------|-------------|-------------|
| `api_error` | 500 | Internal server error |
| `authentication_error` | 401 | Invalid or missing API key |
| `card_error` | 402 | **Charge** declined by card network |
| `idempotency_error` | 409 | Idempotency key reused with different parameters |
| `invalid_request_error` | 400 | Malformed request or missing required parameter |
| `rate_limit_error` | 429 | Too many requests |

## Common Codes

| Code | Type | Cause |
|------|------|-------|
| `card_declined` | card_error | **PaymentMethod** was declined |
| `insufficient_funds` | card_error | Card has no funds |
| `expired_card` | card_error | **PaymentMethod** card is expired |
| `customer_not_found` | invalid_request_error | **Customer** ID does not exist |
| `payment_method_not_attached` | invalid_request_error | **PaymentMethod** not attached to **Customer** |
| `subscription_already_canceled` | invalid_request_error | **Subscription** is already canceled |
| `invoice_already_paid` | invalid_request_error | **Invoice** has already been paid |

## Relationships

- `card_error` always references a **Charge** object in the `charge` field
- `payment_method_not_attached` means a **PaymentMethod** must be attached to the **Customer** first
- Errors on **Subscription** billing trigger `invoice.payment_failed` **Webhook** events

## Retry Logic

- `card_error` — do not retry automatically; notify the user
- `api_error` — safe to retry with exponential backoff
- `rate_limit_error` — retry after the `Retry-After` header duration
- Use `Idempotency-Key` when retrying to avoid duplicate operations
