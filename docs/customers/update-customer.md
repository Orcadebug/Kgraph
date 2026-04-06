# Update a Customer

Updates an existing Customer object.

## Endpoint

```
POST /v1/customers/:id
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | string | yes | The ID of the Customer to update |
| email | string | no | New email address |
| name | string | no | New name |
| default_payment_method | string | no | ID of a PaymentMethod to set as default |
| metadata | object | no | Updated metadata (merged with existing) |

## Returns

Returns the updated **Customer** object.

## Relationships

- Setting `default_payment_method` references an existing **PaymentMethod** that must already be attached to this Customer
- Changes trigger the `customer.updated` **Webhook** event
- Future **Charge** objects will use the new `default_payment_method` unless overridden
- Active **Subscription** billing will use the updated default **PaymentMethod**
