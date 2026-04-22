# Attach a PaymentMethod

Attaches a PaymentMethod to a Customer, making it available for future Charges and Subscriptions.

## Endpoint

```
POST /v1/payment_methods/:id/attach
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | string | yes | The ID of the PaymentMethod to attach |
| customer | string | yes | The ID of the Customer to attach to |

## Returns

Returns the **PaymentMethod** object with `customer` field populated.

## Relationships

- A **PaymentMethod** must be attached to a **Customer** before it can be used for a **Charge**
- After attaching, you can set it as the Customer's `default_payment_method` via Update Customer
- An attached PaymentMethod can be used in **Subscription** creation
- Triggers the `payment_method.attached` **Webhook** event
- A PaymentMethod belongs_to a single Customer at a time; attaching to a new Customer detaches from the old one

## PaymentMethod Types

| Type | Description |
|------|-------------|
| `card` | Credit or debit card |
| `bank_account` | ACH bank account |
| `wallet` | Digital wallet (Apple Pay, Google Pay) |

## Example Request

```bash
curl https://api.niapay.com/v1/payment_methods/pm_xyz789/attach \
  -H "Authorization: Bearer $API_KEY" \
  -d customer=cus_abc123
```
