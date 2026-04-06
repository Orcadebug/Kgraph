# Create a Charge

Creates a new Charge object to bill a Customer or PaymentMethod.

## Endpoint

```
POST /v1/charges
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| amount | integer | yes | Amount in smallest currency unit (e.g., cents) |
| currency | string | yes | Three-letter ISO 4217 currency code |
| customer | string | no | ID of the Customer to charge |
| payment_method | string | no | ID of the PaymentMethod to use |
| description | string | no | Arbitrary string description |
| metadata | object | no | Key-value pairs for your own use |
| capture | boolean | no | Whether to capture immediately (default: true) |

Either `customer` or `payment_method` must be provided.

## Returns

Returns a **Charge** object on success.

## Relationships

- Requires a **Customer** (via `customer`) or a **PaymentMethod** (via `payment_method`)
- If `customer` is provided without `payment_method`, uses the Customer's default PaymentMethod
- A **PaymentMethod** must be attached to the **Customer** before use
- On success, triggers the `charge.succeeded` **Webhook** event
- On failure, triggers the `charge.failed` **Webhook** event
- If this Charge is initiated by an **Invoice**, the Invoice status updates to `paid`
- A failed Charge may be retried; each retry creates a new Charge object

## Example Request

```bash
curl https://api.niapay.com/v1/charges \
  -H "Authorization: Bearer sk_live_..." \
  -d amount=2000 \
  -d currency=usd \
  -d customer=cus_abc123 \
  -d description="Order #1234"
```

## Example Response

```json
{
  "id": "ch_1abc23",
  "object": "charge",
  "amount": 2000,
  "currency": "usd",
  "customer": "cus_abc123",
  "payment_method": "pm_xyz789",
  "status": "succeeded",
  "created": 1712345678
}
```

## Error Codes

- `card_declined` — PaymentMethod was declined
- `insufficient_funds` — Card has insufficient funds
- `invalid_amount` — Amount is below minimum or above maximum
