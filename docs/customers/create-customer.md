# Create a Customer

Creates a new Customer object to represent a buyer in your system.

## Endpoint

```
POST /v1/customers
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| email | string | no | Customer's email address |
| name | string | no | Customer's full name |
| phone | string | no | Customer's phone number |
| metadata | object | no | Arbitrary key-value data |
| payment_method | string | no | ID of an initial PaymentMethod to attach |

## Returns

Returns a **Customer** object.

## Relationships

- A Customer can have multiple **PaymentMethod** objects attached (via `payment_method.attach`)
- A Customer can have multiple **Subscription** objects
- A Customer can have multiple **Charge** objects billed against them
- A Customer generates **Invoice** objects via their Subscriptions
- Creating a Customer triggers the `customer.created` **Webhook** event
- Deleting a Customer triggers the `customer.deleted` **Webhook** event and cancels all active Subscriptions

## Example Request

```bash
curl https://api.niapay.com/v1/customers \
  -H "Authorization: Bearer sk_live_..." \
  -d email="jane@example.com" \
  -d name="Jane Doe"
```

## Example Response

```json
{
  "id": "cus_abc123",
  "object": "customer",
  "email": "jane@example.com",
  "name": "Jane Doe",
  "default_payment_method": null,
  "created": 1712345678
}
```
