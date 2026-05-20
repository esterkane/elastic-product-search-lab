# GrooveGraph

GrooveGraph is a personal music discovery and band research assistant. It is inspired by the earlier UdaPlay agent project, but starts fresh as a full-stack Dockerized application with a Next.js frontend, FastAPI backend, Python worker, and research-friendly datastores.

Spotify authentication is intentionally not implemented yet.

## Stack

- `apps/web`: Next.js, TypeScript, React, Tailwind, Vercel AI SDK
- `apps/api`: Python 3.12, FastAPI, LangGraph, Pydantic
- `apps/worker`: Python background worker sharing backend modules
- Datastores: Postgres, Redis, Weaviate, Neo4j
- Infra: Docker Compose

## Local Setup

1. Copy the environment template:

   ```sh
   cp .env.example .env
   ```

2. Start everything:

   ```sh
   make up
   ```

   Or run Docker Compose directly:

   ```sh
   docker compose up --build
   ```

3. Open the app:

   - Web: http://localhost:3100
   - API health: http://localhost:8100/health

## Make Targets

- `make up`: Build and start all services.
- `make down`: Stop and remove service containers.
- `make logs`: Follow service logs.
- `make test`: Run backend pytest and frontend Vitest suites in containers.
- `make seed`: Run the placeholder seed command.
- `make smoke`: Start services, then verify API health and web boot.

## Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `POSTGRES_DB` | `groovegraph` | Postgres database name |
| `POSTGRES_USER` | `groovegraph` | Postgres user |
| `POSTGRES_PASSWORD` | `groovegraph` | Postgres password |
| `DATABASE_URL` | `postgresql+psycopg://groovegraph:groovegraph@postgres:5432/groovegraph` | Backend database URL |
| `FERNET_SECRET` | unset | Secret used to encrypt OAuth tokens at rest |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `WEAVIATE_URL` | `http://weaviate:8080` | Weaviate HTTP endpoint |
| `NEO4J_URI` | `bolt://neo4j:7687` | Neo4j Bolt URI |
| `NEO4J_USER` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `groovegraph-password` | Neo4j password |
| `SPOTIFY_CLIENT_ID` | unset | Spotify OAuth client id |
| `SPOTIFY_CLIENT_SECRET` | unset | Spotify OAuth client secret |
| `SPOTIFY_REDIRECT_URI` | `http://127.0.0.1:8100/auth/spotify/callback` | Spotify OAuth callback URL |
| `SPOTIFY_LIKED_SONGS_PLAYLIST_ID` | unset | Optional configured Lieblingssongs playlist id |
| `SPOTIFY_LIKED_SONGS_PLAYLIST_NAME` | `Lieblingssongs` | Playlist name fallback for Lieblingssongs sync |
| `DEV_USER_EMAIL` | `listener@groovegraph.local` | Local fallback user until app auth exists |
| `BANDSINTOWN_APP_ID` | unset | Enables upcoming concert lookups |
| `SETLISTFM_API_KEY` | unset | Enables historical setlist and live-history lookups |
| `TICKETMASTER_API_KEY` | unset | Enables optional nearby concert search |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | unset | Optional OpenTelemetry collector endpoint |
| `RATE_LIMIT_ENABLED` | `false` | Enables API request rate limiting |
| `RATE_LIMIT_REQUESTS_PER_MINUTE` | `120` | Per-client request budget when rate limiting is enabled |
| `API_HOST` | `0.0.0.0` | FastAPI bind host |
| `API_PORT` | `8000` | FastAPI container bind port |
| `API_HOST_PORT` | `8100` | Host port mapped to API `8000` |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8100` | Browser-facing API base URL |
| `INTERNAL_API_BASE_URL` | `http://api:8000` | Container-facing API base URL |
| `WEB_PORT` | `3100` | Host port for the web app |
| `POSTGRES_PORT` | `25432` | Host port mapped to Postgres `5432` |
| `REDIS_PORT` | `26379` | Host port mapped to Redis `6379` |
| `WEAVIATE_HTTP_PORT` | `28080` | Host port mapped to Weaviate HTTP `8080` |
| `WEAVIATE_GRPC_PORT` | `25051` | Host port mapped to Weaviate gRPC `50051` |
| `NEO4J_HTTP_PORT` | `27474` | Host port mapped to Neo4j Browser `7474` |
| `NEO4J_BOLT_PORT` | `27687` | Host port mapped to Neo4j Bolt `7687` |

## Service Ports

| Service | Port |
| --- | --- |
| Web | host `3100`, container `3000` |
| API | host `8100`, container `8000` |
| Postgres | host `25432`, container `5432` |
| Redis | host `26379`, container `6379` |
| Weaviate | host `28080`/`25051`, container `8080`/`50051` |
| Neo4j Browser | host `27474`, container `7474` |
| Neo4j Bolt | host `27687`, container `7687` |

## API

`GET /health` returns:

```json
{
  "status": "ok",
  "service": "groovegraph-api"
}
```

`GET /metrics` returns Prometheus-style text metrics for request counts, average latency, tool calls, retrieval events, and token usage counters.

Spotify OAuth and sync endpoints:

- `GET /auth/spotify/login`
- `GET /auth/spotify/callback`
- `POST /auth/spotify/disconnect`
- `GET /me/spotify/status`
- `POST /sync/spotify`
- `GET /me/music-profile`
- `GET /me/tracks`
- `GET /me/artists`
- `POST /spotify/playlists/create-from-recommendations`
- `POST /spotify/playlists/{playlist_id}/add`
- `POST /spotify/tracks/{track_id}/save`
- `GET /spotify/playlists/{playlist_id}/items`

Privacy and compliance endpoints:

- `GET /privacy/export`
- `POST /privacy/delete-my-data`
- `DELETE /sessions/{session_id}`
- `DELETE /recommendations/history`

Privacy rules:

- Spotify data is stored only as needed to operate the app.
- GrooveGraph does not train ML or AI models on Spotify content.
- Full lyrics are not stored unless a licensed provider and plan permits it.
- Web research claims retain source provenance.
- OAuth tokens are encrypted at rest and redacted from logs.

Recommendation endpoints:

- `POST /recommendations/run`
- `GET /recommendations/latest`
- `POST /recommendations/{id}/feedback`
- `POST /recommendations/{id}/create-playlist`

LangGraph chat endpoints:

- `POST /chat`
- `GET /chat/{session_id}`
- `POST /chat/{session_id}/stream`

Concert and live-performance endpoints:

- `GET /artists/{artist_id}/concerts`
- `GET /artists/{artist_id}/setlists`
- `GET /concerts/nearby?city=&country=&radius_km=`
- `GET /concerts/recommended`

Frontend routes:

- `/`
- `/connect`
- `/dashboard`
- `/chat`
- `/recommendations`
- `/artists/[id]`
- `/graph`
- `/concerts`
- `/settings/privacy`

Until first-party app authentication exists, these endpoints resolve a user from `X-User-Id`, `user_id`, or the local `DEV_USER_EMAIL` fallback.

## Development Notes

The backend includes a small LangGraph placeholder in `apps/api/app/graph.py` so the application is ready for future agent workflows. The worker imports the same backend settings and can later be wired to Redis queues, scheduled jobs, or ingestion pipelines.

Alembic migrations run automatically when the API container starts. You can also run them manually with `make migrate`.

## Evaluation Suite

The backend pytest suite is marked by execution layer:

- `unit`: fast, mocked or in-memory tests for agent behavior, scoring, privacy, connectors, and API-adjacent helpers.
- `integration`: tests that require Dockerized backing services such as Neo4j.
- `e2e`: cross-service smoke tests.
- `requires_docker`: tests that assume the Docker Compose stack is running.

`make test` runs the fast backend tests plus frontend component tests. It includes production-like agent evaluations for memory isolation, RAG grounding, query transformation, recommendation explanations, and restricted Spotify endpoint blocking.

`make test-integration` starts Docker Compose, runs Alembic migrations, then executes Docker-backed integration and e2e smoke tests covering `/health`, the web app, a mocked chat request, and graph integration behavior.

## Production Checklist

- Set strong secrets for `FERNET_SECRET`, database passwords, Neo4j password, Spotify client secret, and provider API keys.
- Enable `RATE_LIMIT_ENABLED=true` and tune `RATE_LIMIT_REQUESTS_PER_MINUTE` for the deployment tier.
- Configure `OTEL_EXPORTER_OTLP_ENDPOINT` when an OpenTelemetry collector is available.
- Route JSON logs to a centralized sink and verify token redaction is active.
- Monitor `/metrics` for request volume, latency, tool calls, retrieval counts, and token usage when providers expose it.
- Run `make test`, `make test-integration`, and `docker compose config --quiet` before release.
- Keep OAuth tokens encrypted at rest and never log raw access or refresh tokens.
- Keep source provenance for web claims and avoid storing full lyrics unless licensed.

## Backup Notes

- Postgres: use `pg_dump` for logical backups, encrypt backup artifacts, and test restore into a clean database before each release train.
- Neo4j: use `neo4j-admin database dump` or managed snapshots, keeping graph dumps aligned with the Postgres snapshot time.
- Weaviate: snapshot the persistent volume or use Weaviate backup modules where configured; rebuildable chunks should still retain Postgres source-document provenance.
