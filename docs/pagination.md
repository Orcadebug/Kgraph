# Pagination

All list endpoints use cursor-based pagination for stability and performance.

## How It Works

Cursor pagination uses an item's ID as the cursor rather than a page number, so the results are stable even if new items are inserted.

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `limit` | integer | Number of results to return (1–100, default 10) |
| `starting_after` | string | Return results after this object ID (exclusive) |
| `ending_before` | string | Return results before this object ID (exclusive) |

## Response Shape

```json
{
  "object": "list",
  "data": [ ... ],
  "has_more": true,
  "url": "/v1/charges"
}
```

- `has_more` — whether there are more results beyond this page
- `data` — the current page of objects

## Usage Example

```bash
# First page
curl "https://api.niapay.com/v1/charges?limit=10" \
  -H "Authorization: Bearer $API_KEY"

# Next page (use last ID from previous response)
curl "https://api.niapay.com/v1/charges?limit=10&starting_after=ch_last_id" \
  -H "Authorization: Bearer $API_KEY"
```

## Relationships

- Pagination applies to all list endpoints: **Charge**, **Customer**, **Invoice**, **Subscription**, **PaymentMethod**, and **Webhook** event lists
- The `starting_after` and `ending_before` values must be valid IDs of the object type being listed
- Filtering by **Customer** (`?customer=cus_abc123`) and paginating is the standard way to retrieve a customer's full history
