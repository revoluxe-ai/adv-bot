# WB API OpenAPI swagger inventory

Owner-local / repo snapshot of official Wildberries OpenAPI YAML specs
and URL map for future auto-refresh (INC-RO-02) and path×method analysis
(COL-R03-009 / API Master).

## Current snapshot

| Field | Value |
|-------|--------|
| Snapshot dir | `2026-08-04/` |
| Archive | `2026-08-04/wb-api-swagger.zip` |
| Archive SHA-256 | `7bb4e82a96a1eac6090c85709520007c739e5fa0708ffe9a8002a006d95de1d7` |
| Source portal | `https://dev.wildberries.ru` |
| fetchedAt (from archive) | `2026-08-04T13:53:44.766Z` |
| Sections | **13** (`01`…`13`; no `14-wbd` in this dump) |
| YAML count | 26 (13 en + 13 ru) |

URL map (auto-update source of truth for refresh jobs):

- `2026-08-04/swagger_urls.json`
- `2026-08-04/swagger_urls.txt`

YAML layout:

- `2026-08-04/yaml/en/*.yaml`
- `2026-08-04/yaml/ru/*.yaml`

## Refresh later

1. Re-fetch URLs listed in `swagger_urls.json` → `openapi_yaml_specs`.
2. Replace snapshot dir (or add `YYYY-MM-DD/`).
3. Recompute zip SHA-256 and update this README.
4. Do **not** mass-regenerate all clients until a gap for a specific `spec-key` is proven.

## Note on tooling names

Portal files use `02-items.yaml` / `10-rates.yaml`.
`tools/generate_wb_api_client.py` still maps `products` → historically
`02-products.yaml` — align on next targeted sync.
