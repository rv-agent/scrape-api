# API Documentation Standards

## OpenAPI 3.1 (FastAPI built-in)
- title: ScrapeAPI, version: 1.0.0
- docs_url=None in prod, openapi_url=/api/v1/openapi.json

## Custom Docs (Scalar)
- Scalar API Reference: modern, dark theme, interactive
- Serve at /docs with custom HTML wrapper

## Structure
- /introduction: Overview, getting started
- /authentication: API key usage
- /endpoints: scrape, batch, status, keys, webhooks
- /rate-limits: Tier limits
- /errors: Error codes reference
- /sdks: SDK links (Python, Node, Go)
- /changelog: API versions

## SDK Generation
```bash
openapi-generator generate -i openapi.json -g python -o sdks/python
openapi-generator generate -i openapi.json -g typescript-node -o sdks/node
openapi-generator generate -i openapi.json -g go -o sdks/go
```

## Code Examples
- Python: scrapeapi.Client(api_key).scrape(url)
- Node: new ScrapeAPI(key).scrape(url)
- cURL: POST /api/v1/scrape with Bearer token

## Versioning
- URL: /api/v1/
- Deprecation header: Sunset: Sat, 01 Jan 2027 00:00:00 GMT
- Changelog per version
