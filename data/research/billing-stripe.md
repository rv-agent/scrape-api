# Billing Integration — Stripe

## Architecture
```
User → ScrapeAPI → Stripe Checkout → Stripe Webhook → ScrapeAPI DB
```

## Stripe Products Setup
```python
# Products (created once in Stripe Dashboard)
PRODUCTS = {
    "starter": {"price_id": "price_xxx", "amount": 1900, "requests": 10000},
    "pro": {"price_id": "price_yyy", "amount": 4900, "requests": 50000},
    "enterprise": {"price_id": "price_zzz", "amount": 19900, "requests": -1},  # unlimited
}
```

## Checkout Flow
```python
import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

@app.post("/api/v1/billing/checkout")
async def create_checkout(request: CheckoutRequest, key: APIKey = Depends(get_api_key)):
    session = stripe.checkout.Session.create(
        customer_email=key.email,
        payment_method_types=["card"],
        line_items=[{"price": request.price_id, "quantity": 1}],
        mode="subscription",
        success_url="https://scrapeapi.com/dashboard?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="https://scrapeapi.com/pricing",
        metadata={"api_key_id": str(key.id)},
    )
    return {"checkout_url": session.url}
```

## Webhook Handler
```python
@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)
    except stripe.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")
    
    handlers = {
        "checkout.session.completed": handle_checkout_complete,
        "customer.subscription.updated": handle_subscription_update,
        "customer.subscription.deleted": handle_subscription_cancel,
        "invoice.payment_failed": handle_payment_failed,
    }
    
    handler = handlers.get(event["type"])
    if handler:
        await handler(event["data"]["object"])
    
    return {"status": "ok"}
```

## Usage Metering (Stripe Billing Portal)
- Track `requests_today` in DB
- Monthly reset on subscription anniversary
- Over-limit: return 429 with upgrade prompt
- Stripe Customer Portal for self-service management

## Key Tables
```sql
-- Add to existing schema
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY,
    api_key_id UUID REFERENCES api_keys(id),
    stripe_customer_id TEXT,
    stripe_subscription_id TEXT,
    plan TEXT CHECK(plan IN ('free', 'starter', 'pro', 'enterprise')),
    status TEXT CHECK(status IN ('active', 'past_due', 'canceled', 'trialing')),
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Testing
- Stripe CLI: `stripe listen --forward-to localhost:8000/webhooks/stripe`
- Test cards: `4242 4242 4242 4242` (success), `4000 0000 0000 0002` (decline)
