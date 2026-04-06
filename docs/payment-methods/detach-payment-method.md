# Detach a PaymentMethod

Detaches a PaymentMethod from a Customer. It can no longer be used for Charges or Subscriptions.

## Endpoint

```
POST /v1/payment_methods/:id/detach
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | string | yes | The ID of the PaymentMethod to detach |

## Returns

Returns the **PaymentMethod** object with `customer` set to null.

## Relationships

- Detaches the PaymentMethod from its parent **Customer**
- If this was the Customer's `default_payment_method`, the Customer's default is set to null
- Any active **Subscription** using this PaymentMethod will fail on next billing cycle — update the Subscription's `default_payment_method` before detaching
- Triggers the `payment_method.detached` **Webhook** event
- Detached PaymentMethods cannot be reattached; create a new PaymentMethod instead
