# Getting Started

Welcome to the NiaPay API. This guide helps you make your first API call.

## Base URL

All API requests are made to:

```
https://api.niapay.com/v1
```

## Authentication

All requests require an API key passed as a Bearer token in the `Authorization` header. See the **Authentication** guide for details on obtaining and rotating keys.

## Quick Example

Create your first **Charge** object:

```bash
curl https://api.niapay.com/v1/charges \
  -H "Authorization: Bearer $API_KEY" \
  -d amount=2000 \
  -d currency=usd \
  -d customer=cus_abc123
```

## Core Objects

The API revolves around a set of interconnected objects:

- **Customer** — represents a buyer in your system
- **Charge** — a payment attempt against a Customer or PaymentMethod
- **PaymentMethod** — a card or bank account attached to a Customer
- **Subscription** — recurring billing tied to a Customer
- **Invoice** — generated automatically by a Subscription each billing cycle
- **Webhook** — real-time event notifications for all state changes

## Relationships

- A **Charge** requires either a **Customer** or a **PaymentMethod**
- A **PaymentMethod** belongs_to a **Customer**
- A **Subscription** belongs_to a **Customer** and generates **Invoice** objects
- An **Invoice** can trigger a **Charge**
- All major state changes trigger **Webhook** events

## Error Handling

All errors follow a consistent structure. See the **Errors** reference for codes and retry logic.

## Pagination

All list endpoints support cursor-based **Pagination**. See the Pagination guide.
