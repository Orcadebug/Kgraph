# Retrieve a Customer

Retrieves a Customer object by ID.

## Endpoint

```
GET /v1/customers/:id
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | string | yes | The ID of the Customer |

## Returns

Returns a **Customer** object, including:
- `default_payment_method` — the Customer's default **PaymentMethod** ID
- `subscriptions` — list of active **Subscription** IDs
- `invoice_settings` — default settings for **Invoice** generation

## Relationships

- References attached **PaymentMethod** objects via `default_payment_method`
- References active **Subscription** objects
- **Invoice** and **Charge** history is retrievable via list endpoints filtered by this Customer ID
