# Pay an Invoice

Manually triggers payment of an open Invoice.

## Endpoint

```
POST /v1/invoices/:id/pay
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | string | yes | The ID of the Invoice to pay |
| payment_method | string | no | PaymentMethod to use (overrides Customer default) |
| forgive | boolean | no | If true, mark Invoice paid even if Charge fails |

## Returns

Returns the **Invoice** object with updated `status` and `charge` fields.

## Relationships

- Creates a **Charge** against the Invoice's **Customer** using the specified or default **PaymentMethod**
- On success: Invoice `status` → `paid`, triggers `invoice.paid` **Webhook** event and `charge.succeeded` event
- On failure: triggers `invoice.payment_failed` and `charge.failed` **Webhook** events
- If the Invoice belongs to a **Subscription**, a failed payment may pause or cancel the Subscription depending on your retry settings
- Using `forgive: true` marks the Invoice paid without a Charge — useful for comps or write-offs

## Retry Logic

Automatic retries are configured in your account's billing settings. Manual pay always attempts immediately regardless of retry schedule.
