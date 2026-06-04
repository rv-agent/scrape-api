#!/bin/bash
# ScrapeAPI Load Test Script
# Uses Apache Bench (ab) or wrk for load testing
set -e

BASE_URL="${1:-http://localhost:8000}"
API_KEY="${2:-sk-dev...mnop}"
REQUESTS="${3:-1000}"
CONCURRENCY="${4:-10}"

echo "═══════════════════════════════════════"
echo "  ScrapeAPI Load Test"
echo "═══════════════════════════════════════"
echo "  Target: $BASE_URL"
echo "  Requests: $REQUESTS"
echo "  Concurrency: $CONCURRENCY"
echo "═══════════════════════════════════════"

# Health check
echo ""
echo "▶ Health check..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health")
if [ "$HTTP_CODE" != "200" ]; then
    echo "✗ Health check failed: $HTTP_CODE"
    exit 1
fi
echo "✓ Health: $HTTP_CODE"

# Test 1: Health endpoint
echo ""
echo "▶ Test 1: Health endpoint ($REQUESTS requests)..."
ab -n "$REQUESTS" -c "$CONCURRENCY" -q "$BASE_URL/health" 2>&1 | grep -E "(Requests per second|Time per request|Failed|Non-2xx)"

# Test 2: API key validation
echo ""
echo "▶ Test 2: API validation ($REQUESTS requests)..."
ab -n "$REQUESTS" -c "$CONCURRENCY" -q \
    -H "X-API-Key: $API_KEY" \
    "$BASE_URL/api/v1/keys/usage" 2>&1 | grep -E "(Requests per second|Time per request|Failed|Non-2xx)"

# Test 3: Scrape endpoint (lighter load)
LIGHT_REQUESTS=$((REQUESTS / 10))
echo ""
echo "▶ Test 3: Scrape endpoint ($LIGHT_REQUESTS requests)..."
ab -n "$LIGHT_REQUESTS" -c "$CONCURRENCY" -q \
    -H "X-API-Key: $API_KEY" \
    -H "Content-Type: application/json" \
    -p /dev/stdin \
    "$BASE_URL/api/v1/scrape" <<< '{"url":"https://httpbin.org/html"}' 2>&1 | grep -E "(Requests per second|Time per request|Failed|Non-2xx)"

echo ""
echo "═══════════════════════════════════════"
echo "  Load Test Complete"
echo "═══════════════════════════════════════"
