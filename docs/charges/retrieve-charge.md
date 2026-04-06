# Retrieve a Charge

Retrieves the details of an existing Charge.

## Endpoint

```
GET /v1/charges/:id
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| id | string | yes | The ID of the Charge to retrieve |

## Returns

Returns a **Charge** object.

## Relationships

- The Charge references its parent **Customer** via `customer` field
- The Charge references its **PaymentMethod** via `payment_method` field
- If created by a **Subscription** cycle, the `invoice` field references the **Invoice**
- Refunds associated with this Charge are listed in the `refunds` array

## Example Request

```bash
curl https://api.niapay.com/v1/charges/ch_1abc23 \
  -H "Authorization: Bearer sk_live_..."
```
