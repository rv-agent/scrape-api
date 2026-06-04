# Proxy Rotation Techniques

## Current (Phase 4)
- ProxyManager: round-robin, random, fastest strategies
- Health tracking, circuit breaker, async health check

## Enhancements

### Geo-Targeting
- Region-tagged proxies, fallback to global pool
- Use: local content, language-specific pages

### Proxy Providers
- Bright Data: Residential/DC, $500+/mo, enterprise
- Smartproxy: Residential, $75+/mo, pro tier
- IPRoyal: Residential/DC, $20+/mo, starter

### Health Check
- Interval: configurable (default 60s)
- Endpoint: httpbin.org/ip
- Track: latency, success rate, last check time
- Unhealthy after 3 consecutive fails, auto-recover after 1 success

### Proxy Types
- Datacenter: Fast, cheap, easily detected
- Residential: Real IPs, expensive, harder to detect
- Mobile: Carrier IPs, most expensive, best anti-detection
- ISP: DC speed + residential IP, mid-range

### Rotation Per Need
- Per-request: anti-detection
- Per-session: login-based sites
- Per-domain: rate-limited sites
- Weighted: prefer faster/healthier

### Failover Chain
Primary (residential) -> Secondary (datacenter) -> Direct (no proxy)

### Cost Optimization
- Cache results, reduce requests
- DC for non-sensitive targets
- Residential only for anti-bot sites
- Track cost per scrape in metrics
