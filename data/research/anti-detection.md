# Anti-Detection Methods

## Fingerprint Categories
1. Browser: UA, platform, plugins, WebGL, Canvas
2. Network: TLS version, cipher suites, HTTP/2 settings
3. Behavioral: Mouse movements, scroll patterns, timing

## TLS Fingerprinting
- httpx default TLS fingerprint is detectable
- Use curl_cffi for browser-like TLS impersonation
```python
from curl_cffi.requests import AsyncSession
async with AsyncSession(impersonate='chrome120') as s:
    resp = await s.get(url)
```

## Browser Stealth (Playwright)
- Override navigator.webdriver = false
- Spoof plugins, languages, chrome.runtime
- Realistic viewport: 1920x1080

## Detection vs Bypass
| Method | Bypass |
|--------|--------|
| navigator.webdriver | Override property |
| Canvas fingerprint | Randomize pixels |
| WebGL fingerprint | Spoof vendor/renderer |
| TLS JA3 | tls_client/curl_cffi |
| Request timing | Random delays |
| Honeypot links | Parse carefully |

## Stack Recommendation
- Static: curl_cffi (TLS matching)
- Dynamic: Playwright + stealth patches
- Hard targets: Playwright + residential proxy + human delays

## Human-Like Behavior
- Random delays: 500ms-3s between actions
- Scroll: random distance, variable speed
- Mouse: random movements before click
- Typing: character-by-character with delays

## Detection Testing
- bot.sannysoft.com (browser bot detection)
- creepjs (fingerprinting score)
- nowsecure.nl (Cloudflare challenge)
- Aim for > 90% not-a-bot rating
