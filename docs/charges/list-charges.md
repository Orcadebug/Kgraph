# List Charges

Returns a paginated list of Charges.

## Endpoint

```
GET /v1/charges
```

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| customer | string | no | Filter by Customer ID |
| limit | integer | no | Number of results (1–100, default 10) |
| starting_after | string | no | Cursor for Pagination (Charge ID) |
| ending_before | string | no | Cursor for Pagination (Charge ID) |

## Returns

Returns a paginated list of **Charge** objects.

## Relationships

- Filtered by **Customer** when `customer` parameter is provided
- Uses cursor-based **Pagination** via `starting_after` / `ending_before`
- Each Charge in the list references a **PaymentMethod** and optionally an **Invoice**

## Example Request

```bash
curl "https://api.niapay.com/v1/charges?customer=cus_abc123&limit=5" \
  -H "Authorization: Bearer sk_live_..."
```
