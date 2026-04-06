# Create a Subscription

Creates a recurring billing Subscription for a Customer.

## Endpoint

```
POST /v1/subscriptions
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| customer | string | yes | ID of the Customer to subscribe |
| price | string | yes | ID of the Price (amount + interval) |
| default_payment_method | string | no | PaymentMethod to use for billing (falls back to Customer default) |
| trial_end | integer | no | Unix timestamp for trial period end |
| metadata | object | no | Arbitrary key-value data |
| cancel_at_period_end | boolean | no | Cancel at end of current billing period |

## Returns

Returns a **Subscription** object.

## Relationships

- A Subscription belongs_to a **Customer**
- A Subscription uses a **PaymentMethod** (directly set, or inherited from Customer's default)
- At each billing cycle, a Subscription automatically generates an **Invoice**
- The Invoice then initiates a **Charge** against the Customer's PaymentMethod
- Triggers the `subscription.created` **Webhook** event
- If a trial is set, triggers `customer.subscription.trial_will_end` 3 days before trial_end
- A failed Charge during renewal triggers `invoice.payment_failed` and may pause the Subscription

## Billing Cycle

```
Subscription cycle → Invoice created → Charge attempted → charge.succeeded → Invoice paid
                                                         ↘ charge.failed → invoice.payment_failed
```

## Example Request

```bash
curl https://api.niapay.com/v1/subscriptions \
  -H "Authorization: Bearer sk_live_..." \
  -d customer=cus_abc123 \
  -d price=price_monthly_pro
```
