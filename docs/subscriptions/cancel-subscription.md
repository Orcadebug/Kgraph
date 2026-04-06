# Cancel a Subscription

Cancels an active Subscription immediately or at the end of the current billing period.

## Endpoint

```
DELETE /v1/subscriptions/:id
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | string | yes | The ID of the Subscription to cancel |
| cancel_at_period_end | boolean | no | If true, cancel at period end instead of immediately |

## Returns

Returns the **Subscription** object with `status` set to `canceled` (or `active` with `cancel_at_period_end: true`).

## Relationships

- Canceling a Subscription triggers the `customer.subscription.deleted` **Webhook** event
- Any pending **Invoice** for the canceled Subscription will be voided
- If canceled mid-period, a prorated credit **Invoice** may be generated depending on your proration settings
- Deleting a **Customer** automatically cancels all their active Subscriptions
- A canceled Subscription's historical **Charge** and **Invoice** objects are preserved

## Final Invoice

If `cancel_at_period_end` is false and the Customer has used service this period, a final Invoice is generated and a Charge is attempted immediately.
