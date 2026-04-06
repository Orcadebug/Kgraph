# Webhook Events

Webhooks notify your server in real-time when events occur in NiaPay. Each event has a `type` and a `data.object` payload.

## Event Types

### Charge Events

| Event | Description |
|-------|-------------|
| `charge.succeeded` | A **Charge** was successfully processed |
| `charge.failed` | A **Charge** attempt failed |
| `charge.refunded` | A **Charge** was partially or fully refunded |
| `charge.dispute.created` | A **Customer** initiated a dispute (chargeback) |

### Customer Events

| Event | Description |
|-------|-------------|
| `customer.created` | A new **Customer** was created |
| `customer.updated` | A **Customer** was updated |
| `customer.deleted` | A **Customer** was deleted |
| `customer.subscription.trial_will_end` | A **Subscription** trial ends in 3 days |
| `customer.subscription.deleted` | A **Subscription** was canceled |

### Invoice Events

| Event | Description |
|-------|-------------|
| `invoice.created` | A new **Invoice** was created |
| `invoice.paid` | An **Invoice** was paid via a **Charge** |
| `invoice.payment_failed` | Payment of an **Invoice** failed |
| `invoice.voided` | An **Invoice** was voided |

### PaymentMethod Events

| Event | Description |
|-------|-------------|
| `payment_method.attached` | A **PaymentMethod** was attached to a **Customer** |
| `payment_method.detached` | A **PaymentMethod** was detached from a **Customer** |

## Relationships

- Charge events reference the **Charge** object and its parent **Customer**
- Invoice events reference the **Invoice** and its parent **Subscription** and **Customer**
- PaymentMethod events reference the **PaymentMethod** and its **Customer**
- All events are delivered to your registered **Webhook** endpoint URLs
- Signatures are verified using **Webhook** signatures (see Webhook Signatures)

## Event Object Structure

```json
{
  "id": "evt_abc123",
  "object": "event",
  "type": "charge.succeeded",
  "created": 1712345678,
  "data": {
    "object": { ... }
  }
}
```
