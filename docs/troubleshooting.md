# Troubleshooting

## Elasticsearch Is Unreachable

Run:

```powershell
docker compose ps
.\scripts\check-es.ps1
```

If security is enabled, confirm `.env` has the local Elasticsearch credentials and `ELASTICSEARCH_USE_AUTH=true` when needed.

## `products-read` Returns No Results

The API now defaults to `products-read`. Build and switch an index:

```powershell
.\.venv\Scripts\python.exe scripts\load_sample_data.py --switch-alias --install-resources
```

Check the alias:

```powershell
.\.venv\Scripts\python.exe scripts\switch_product_alias.py --target-index products-vYOURBUILD
```

## Kafka Publish Fails

Kafka support is optional. Install the extra and start Redpanda:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[kafka]"
docker compose -f docker-compose.yml -f docker-compose.kafka.yml up -d redpanda redpanda-console
```

Malformed events should go to DLQ through the consumer path. Producer delivery failures are retryable broker errors.

## API Tests Cannot Find Vitest

Install API dependencies:

```powershell
cd apps\api
npm install
npm test
```

CI uses `npm ci` from `apps/api/package-lock.json`.

## Pytest Temp Directory Permission Errors On Windows

In the Codex sandbox, pytest fixtures using `tmp_path` can fail against the user temp directory. Running the same command outside the sandbox has passed consistently:

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider tests\python
```

## Policies Do Not Fire

Confirm:

- `SEARCH_POLICY_PATH` points to a JSON file.
- the policy has `enabled: true`.
- the query contains the policy `queryMatch` text.
- `debug=true` is set so fired policies are visible.

## Suggest Returns Empty

Build the separate suggest index:

```powershell
.\.venv\Scripts\python.exe scripts\build_product_suggest_index.py --input data\sample\products.jsonl --index product-suggest --recreate
```
