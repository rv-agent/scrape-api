# Subscription Model Design

## Tier Structure
| Tier | Price | Requests/mo | Batch Size | Proxy | Webhook | Support |
|------|-------|-------------|------------|-------|---------|---------|
| Free | $0 | 100 | 5 | Shared | No | Community |
| Starter | $19 | 10,000 | 20 | Shared | Yes | Email |
| Pro | $49 | 50,000 | 50 | Dedicated | Yes | Priority |
| Enterprise | $199+ | Unlimited | 200 | Custom | Yes | SLA |

## Usage Metering Strategy
- Track per API key: `requests_today`, `requests_this_month`
- Reset monthly on subscription start date (not calendar month)
- Real-time check before processing request
```python
async def check_usage_limit(key: APIKey) -> bool:
    if key.tier == "enterprise":
        return True
    usage = await get_monthly_usage(key.id)
    return usage < TIER_LIMITS[key.tier]
```

## Upgrade/Downgrade Flow
- **Upgrade**: Immediate, prorated billing
- **Downgrade**: End of current period
- **Cancel**: End of period, keep data 30 days
- **Reactivate**: Within 30 days, restore data

## Trial Strategy
- 7-day free trial for Starter/Pro
- No credit card required for Free tier
- Trial → auto-downgrade to Free if no payment

## Overage Handling
- Soft limit: 429 response with `X-Upgrade-Available: true`
- Hard limit at 120%: Block requests
- Email notification at 80%, 100%, 120%
- Optional: Pay-per-use overage ($0.001/request for Starter)

## Annual Discount
- 20% off for annual billing
- Stripe: `recurring.interval=year` with discounted price IDs
