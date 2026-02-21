# Prism — User Stories

> Development-ready user stories for the Prism AI News Intelligence Platform.
> Each story follows: **Story** → **Acceptance Criteria** → **Technical Implementation Notes**.

---

## Epic 1: Infrastructure & DevOps Foundation

### E1-S1: Docker Compose Service Orchestration

**Story:** As a Platform Engineer, I want a single `docker-compose up` command that boots every infrastructure dependency so that any developer can run the full stack locally without manual service setup.

**Acceptance Criteria:**
- Running `docker-compose up -d` starts PostgreSQL, Redis, RabbitMQ, MinIO, Qdrant, Airflow (init, webserver, scheduler, worker), Prometheus, and Grafana. Ollama is started only when using the optional profile: `docker-compose --profile llm-local up -d`.
- Each service exposes its UI/port on the host and passes its configured health check within 60 seconds.
- All services communicate on a shared Docker bridge network.
- Named volumes persist data across container restarts.
- A `.env.example` file documents every required variable with safe defaults.

**Technical Implementation Notes:**
- `docker-compose.yml` defines each service with `healthcheck`, `depends_on` (condition: service_healthy), and environment variable substitution from `.env`.
- PostgreSQL (asyncpg) on port 5435, Redis on 6380, RabbitMQ (management UI) on 15672, MinIO console on 9001, Qdrant HTTP on 6336, Airflow webserver on 8080.
- Prometheus scrapes from a `prometheus.yml` mounted from `observability/prometheus/`. Grafana auto-provisions datasources and dashboards from `observability/grafana/provisioning/`.
- Ollama service uses the `ollama/ollama` image, exposes port 11434, and mounts a volume for downloaded models. Tagged as an optional profile (`--profile llm-local`).

---

### E1-S2: Database Migration Framework

**Story:** As a Platform Engineer, I want an automated database migration system so that schema changes are versioned, reproducible, and applied consistently across all environments.

**Acceptance Criteria:**
- Alembic is initialized with async support pointing at the PostgreSQL instance.
- Running `alembic upgrade head` applies all pending migrations.
- Running `alembic revision --autogenerate -m "..."` detects model changes and generates a migration script.
- Migration history is stored in the `alembic_version` table in PostgreSQL.

**Technical Implementation Notes:**
- Alembic configured in `src/db/alembic.ini` with `sqlalchemy.url` reading from `Settings.async_database_url`.
- `env.py` imports `Base` from `src/shared/database/postgres/base.py` and all model modules to enable autogenerate.
- Uses `asyncpg` driver via SQLAlchemy async engine. Alembic's async migration runner (`run_async_migrations`) is used in `env.py`.

---

### E1-S3: Environment Configuration & Secrets Management

**Story:** As a Platform Engineer, I want a centralized, validated configuration system so that all services read settings from a single source of truth with clear defaults and secret handling.

**Acceptance Criteria:**
- All runtime configuration is managed through a Pydantic `Settings` class that reads from environment variables and `.env`.
- Sensitive values (passwords, API keys, Sentry DSN, LangSmith/Langfuse API keys) use `SecretStr`.
- Computed fields produce connection URLs for Postgres (async/sync), RabbitMQ, Redis, MinIO, Qdrant, and Ollama.
- LLM provider settings are present: `LLM_DEFAULT_PROVIDER`, `LLM_DEFAULT_MODEL`, and per-role overrides (`LLM_MAP_PROVIDER`, `LLM_MAP_MODEL`, `LLM_JUDGE_PROVIDER`, `LLM_JUDGE_MODEL`, etc.).
- A `.env.example` is committed to the repo with every variable documented.

**Technical Implementation Notes:**
- `src/core/config.py` extends the existing `Settings(BaseSettings)` class.
- `pydantic-settings` reads `.env` with `SettingsConfigDict`. `secrets_dir='/run/secrets'` supports Docker Swarm/Kubernetes secret mounts.
- New fields: `sentry_dsn`, `langsmith_api_key`, `langfuse_public_key`, `langfuse_secret_key`, `langfuse_host`, `ollama_host`, `llm_default_provider`, `llm_default_model`, plus per-role LLM overrides.

---

### E1-S4: Ollama Local LLM Service

**Story:** As a Platform Engineer, I want an optional Ollama service in Docker Compose so that developers can run LLM inference locally without requiring cloud API keys.

**Acceptance Criteria:**
- `docker-compose --profile llm-local up ollama` starts the Ollama container.
- The Ollama API is accessible at `http://ollama:11434` from within the Docker network.
- Downloaded models persist across restarts via a named volume.
- The service is not started by default (profile-gated) to avoid GPU/memory overhead for developers who use cloud APIs.

**Technical Implementation Notes:**
- Docker Compose service uses `ollama/ollama:latest` image with profile `llm-local`.
- Volume `ollama_models` mounted at `/root/.ollama`.
- `OLLAMA_HOST` environment variable set in `.env.example` with default `http://ollama:11434`.
- LangChain's `ChatOllama` uses this host when the provider config resolves to `ollama`.

---

### E1-S5: Prometheus & Exporters Deployment

**Story:** As a Platform Engineer, I want Prometheus deployed with scrape targets for every infrastructure service so that time-series metrics are collected automatically.

**Acceptance Criteria:**
- Prometheus container starts and scrapes itself, the FastAPI `/metrics` endpoint, postgres_exporter, redis_exporter, RabbitMQ's built-in Prometheus endpoint, and Airflow's StatsD exporter.
- Scrape targets are defined declaratively in `prometheus.yml`.
- Alerting rules for critical thresholds are loaded from `observability/prometheus/alerts/`.
- Prometheus UI is accessible on port 9090.

**Technical Implementation Notes:**
- `observability/prometheus/prometheus.yml` defines `scrape_configs` for each target.
- `postgres_exporter` and `redis_exporter` run as sidecar containers in Docker Compose, each connecting to their respective service.
- RabbitMQ exposes `/api/metrics` natively when the `rabbitmq_prometheus` plugin is enabled (set via `RABBITMQ_PLUGINS` env var).
- Airflow StatsD metrics are forwarded through a `statsd-exporter` sidecar that translates them to Prometheus format.

---

### E1-S6: Grafana Provisioned Dashboards

**Story:** As a Platform Engineer, I want Grafana pre-configured with datasources and dashboards so that observability is available out-of-the-box without manual setup.

**Acceptance Criteria:**
- Grafana starts with Prometheus as a provisioned datasource (no manual configuration needed).
- At least four dashboards are provisioned: System Overview, API Performance, Ingestion Pipeline Health, and LLM Cost Tracking.
- Grafana UI is accessible on port 3000 with default admin credentials from `.env`.

**Technical Implementation Notes:**
- `observability/grafana/provisioning/datasources/prometheus.yml` defines the Prometheus datasource.
- `observability/grafana/provisioning/dashboards/` contains JSON dashboard definitions and a `dashboards.yml` provider config.
- Grafana Docker Compose service mounts the `observability/grafana/provisioning/` directory.

---

### E1-S7: Sentry Project Configuration

**Story:** As a Platform Engineer, I want Sentry DSNs configured for both backend and frontend so that runtime errors and performance data are captured from day one.

**Acceptance Criteria:**
- `SENTRY_DSN_BACKEND` and `SENTRY_DSN_FRONTEND` are defined in `.env.example`.
- The FastAPI app initializes `sentry_sdk` on startup with the backend DSN, traces sample rate, and environment tag.
- The React app initializes `Sentry.init()` with the frontend DSN, browser tracing, and session replay.
- Sentry initialization is skipped gracefully if the DSN is empty (local development).

**Technical Implementation Notes:**
- Backend: `sentry-sdk[fastapi]` Python package. Initialized in the FastAPI lifespan handler; reads `settings.sentry_dsn`.
- Frontend: `@sentry/react` and `@sentry/browser` npm packages. Initialized in `frontend/src/app/sentry.ts`.
- Both set `environment` (local/staging/production) from config and `release` from a build-time variable.

---

### E1-S8: LangSmith / Langfuse Tracing Configuration

**Story:** As a Platform Engineer, I want agent tracing infrastructure configured so that every LangGraph execution is automatically logged to LangSmith or Langfuse.

**Acceptance Criteria:**
- Environment variables for LangSmith (`LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT`) or Langfuse (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST`) are present in `.env.example`.
- When configured, all LangChain/LangGraph invocations automatically export traces without code changes in the graph definitions.
- Tracing is disabled when keys are absent (no startup errors).

**Technical Implementation Notes:**
- LangSmith: Setting `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` automatically enables tracing for all LangChain/LangGraph calls (zero-code integration).
- Langfuse: The `langfuse` Python package provides a `CallbackHandler` that is attached globally via the LLM factory in `ai/llm/callbacks.py`.
- The tracing provider is selected by the `TRACING_PROVIDER` env var (`langsmith` | `langfuse` | `none`).

---

## Epic 2: Authentication & User Management

### E2-S1: User Registration

**Story:** As a Consumer, I want to create an account with my email and password so that I can access personalized features like watchlists and chat history.

**Acceptance Criteria:**
- `POST /api/v1/auth/register` accepts `email`, `password`, and optional `display_name`.
- Passwords are hashed with bcrypt before storage.
- Duplicate email returns 409 Conflict.
- Successful registration returns the user object (without password) and a JWT access token.
- The user row is created in PostgreSQL with `role=consumer` by default.

**Technical Implementation Notes:**
- FastAPI route in `src/api/v1/auth.py`. Pydantic schema validates input.
- `passlib[bcrypt]` hashes passwords. User model in `src/shared/database/postgres/models/user.py` extended with `email`, `hashed_password`, `role`, `display_name`.
- JWT issued via `python-jose` with `settings.jwt_secret_key` and configurable expiry.
- Async session from `src/shared/database/clients/postgres.py` handles the DB write.

---

### E2-S2: User Login & JWT Issuance

**Story:** As a Consumer, I want to log in with my email and password so that I receive a token to authenticate subsequent requests.

**Acceptance Criteria:**
- `POST /api/v1/auth/login` accepts `email` and `password`.
- Returns a JWT access token and a refresh token on success.
- Invalid credentials return 401 Unauthorized.
- The JWT payload contains `sub` (user ID), `role`, and `exp`.

**Technical Implementation Notes:**
- FastAPI route in `src/api/v1/auth.py`. Verifies bcrypt hash against stored `hashed_password`.
- Access token: short-lived (15 min). Refresh token: longer-lived (7 days), stored in Redis keyed by user ID for revocation.
- `python-jose` encodes/decodes tokens. Signing algorithm: HS256 with `settings.jwt_secret_key`.

---

### E2-S3: JWT Authentication Dependency

**Story:** As a Platform Engineer, I want a reusable FastAPI dependency that extracts and validates the JWT from incoming requests so that protected endpoints are secured uniformly.

**Acceptance Criteria:**
- A `get_current_user` dependency extracts the `Authorization: Bearer <token>` header, decodes the JWT, and returns the user record.
- Expired or invalid tokens return 401.
- The dependency is composable: `get_current_admin` wraps it to require `role=admin`.

**Technical Implementation Notes:**
- Defined in `src/api/deps.py`. Uses FastAPI's `Depends()` and `HTTPBearer` security scheme.
- Decodes with `python-jose`, then fetches the user from PostgreSQL (cached in Redis for high-frequency endpoints).
- `get_current_enterprise` variant checks `role=enterprise` for B2B endpoints.

---

### E2-S4: B2B API Key Management

**Story:** As an Enterprise Client, I want to generate and manage API keys so that my automated systems can authenticate with the Prism API without user-interactive login.

**Acceptance Criteria:**
- `POST /api/v1/auth/api-keys` (authenticated, enterprise role) creates a new API key with an optional label.
- The raw key is returned once on creation; only a hashed version is stored.
- `GET /api/v1/auth/api-keys` lists active keys (label, created_at, last_used_at; no raw key).
- `DELETE /api/v1/auth/api-keys/{key_id}` revokes a key.
- API key authentication works via `X-API-Key` header as an alternative to JWT.

**Technical Implementation Notes:**
- `ApiKey` model in PostgreSQL: `id`, `user_id` (FK), `hashed_key`, `label`, `created_at`, `last_used_at`, `is_active`.
- Key generated with `secrets.token_urlsafe(32)`, hashed with SHA-256 before storage.
- FastAPI dependency `get_current_user_or_api_key` checks for JWT first, then falls back to `X-API-Key` header lookup.

---

### E2-S5: Role-Based Access Control

**Story:** As a System Administrator, I want role-based access control so that consumers, enterprise clients, and admins can only access features appropriate to their tier.

**Acceptance Criteria:**
- Three roles exist: `consumer`, `enterprise`, `admin`.
- Consumer endpoints (feed, chat, watchlists) are accessible to all authenticated users.
- Enterprise endpoints (firehose WebSocket, private RAG workspace, API key management) require `enterprise` or `admin` role.
- Admin endpoints (pipeline management, observability, user management) require `admin` role.
- Unauthorized role access returns 403 Forbidden.

**Technical Implementation Notes:**
- Role is stored as an enum column on the `User` model in PostgreSQL.
- `RoleChecker` dependency in `src/api/deps.py` accepts a list of allowed roles and wraps `get_current_user`.
- Applied via `Depends(RoleChecker(["admin"]))` on admin route definitions.

---

### E2-S6: Subscription Tier Management

**Story:** As a Consumer, I want to upgrade or downgrade my subscription tier so that I can unlock premium features like unlimited chat queries and advanced alerts.

**Acceptance Criteria:**
- `GET /api/v1/subscriptions/tiers` returns available tiers (Free, Pro, Enterprise) with feature limits.
- `POST /api/v1/subscriptions` changes the user's tier (placeholder for payment integration).
- The user's current tier is reflected in `GET /api/v1/auth/me`.
- Rate limits and feature gates reference the user's tier.

**Technical Implementation Notes:**
- `Subscription` model in PostgreSQL: `id`, `user_id` (FK), `tier` (enum), `started_at`, `expires_at`.
- `src/services/subscription_service.py` encapsulates tier logic.
- Rate limiting (Redis-based) reads `tier` to determine per-endpoint limits (e.g., Free: 10 chat msgs/day, Pro: 100).

---

## Epic 3: Core Backend API (FastAPI)

### E3-S1: Application Bootstrap & Lifespan

**Story:** As a Platform Engineer, I want the FastAPI application to initialize and tear down all external connections (database, Redis, RabbitMQ) in a managed lifespan so that resources are handled cleanly.

**Acceptance Criteria:**
- The FastAPI app uses an async lifespan context manager.
- On startup: initializes the Postgres engine, Redis connection pool, Qdrant client, Sentry SDK, and Prometheus instrumentator.
- On shutdown: closes Postgres engine, Redis pool, and any open RabbitMQ connections.
- A `GET /health` endpoint returns 200 with the status of each dependency (Postgres ping, Redis ping, Qdrant health).

**Technical Implementation Notes:**
- `src/api/main.py` defines `app = FastAPI(lifespan=lifespan)`.
- The `lifespan` async generator calls `postgres.get_engine()`, `redis.get_pool()`, etc. on startup and their `.close()` on shutdown.
- Health check calls `postgres.ping()`, `redis.ping()`, and Qdrant's `/healthz` endpoint. Returns a JSON dict with per-service status.
- `prometheus_fastapi_instrumentator` is initialized and `.instrument(app)` is called in the lifespan.
- `sentry_sdk.init()` with FastAPI integration is called if `settings.sentry_dsn` is set.

---

### E3-S2: Redis Caching Layer

**Story:** As a Platform Engineer, I want a Redis-backed caching layer so that high-volume read endpoints (feed, entity context) serve responses with sub-10ms latency.

**Acceptance Criteria:**
- An async Redis client is initialized on app startup and available via dependency injection.
- A `@cache(ttl=...)` decorator or utility function caches serialized endpoint responses keyed by URL + query params.
- Cache invalidation occurs when the ingestion pipeline writes new event clusters.
- Cache hit/miss ratio is exposed as a Prometheus counter.

**Technical Implementation Notes:**
- `src/shared/redis/client.py` wraps `redis.asyncio.Redis` with connection pooling.
- Cache keys follow the pattern `cache:{endpoint}:{hash(params)}`. TTL defaults to 5 minutes for feed endpoints.
- Invalidation: the ingestion worker publishes a Redis `PUBLISH` on channel `cache:invalidate` with the affected entity/cluster ID; the FastAPI app subscribes and deletes matching keys.
- Prometheus counters: `prism_cache_hits_total`, `prism_cache_misses_total`.

---

### E3-S3: Rate Limiting

**Story:** As a Platform Engineer, I want rate limiting on API endpoints so that no single user or API key can overwhelm the system.

**Acceptance Criteria:**
- Rate limits are enforced per user/API key using a sliding window algorithm.
- Limits vary by subscription tier (Free: 60 req/min, Pro: 300 req/min, Enterprise: 1000 req/min).
- Exceeding the limit returns 429 Too Many Requests with a `Retry-After` header.
- Rate limit state is stored in Redis with automatic expiry.

**Technical Implementation Notes:**
- Implemented as FastAPI middleware or dependency in `src/api/deps.py`.
- Redis sorted sets implement the sliding window: `ZADD` with timestamp scores, `ZRANGEBYSCORE` to count recent requests, `ZREMRANGEBYSCORE` to evict expired entries.
- Tier is resolved from the authenticated user's subscription via `get_current_user`.
- Prometheus counter `prism_rate_limit_exceeded_total` labeled by tier.

---

### E3-S4: REST API Versioned Routing

**Story:** As a Platform Engineer, I want versioned API routing so that future breaking changes can coexist with the current contract.

**Acceptance Criteria:**
- All endpoints live under `/api/v1/`.
- A versioned router is defined in `src/api/v1/` and mounted on the main app.
- OpenAPI documentation is auto-generated at `/docs` and `/redoc`.
- CORS middleware is configured for the frontend origin.

**Technical Implementation Notes:**
- `src/api/main.py` mounts `v1_router` at prefix `/api/v1`.
- `v1_router` includes sub-routers from `auth.py`, `feed.py`, `chat.py`, `watchlists.py`, `firehose_ws.py`, `rag_workspace.py`, `admin.py`.
- `CORSMiddleware` allows `settings.frontend_origin` (default `http://localhost:3000`).
- FastAPI auto-generates OpenAPI schema; `Helmet`-equivalent security headers added via middleware.

---

### E3-S5: WebSocket Support

**Story:** As a Platform Engineer, I want WebSocket support in FastAPI so that B2B clients can receive real-time streaming data and B2C clients can use live chat.

**Acceptance Criteria:**
- FastAPI WebSocket endpoints are defined and accept connections.
- Authentication is performed on the WebSocket handshake (JWT or API key via query param).
- Connections are tracked in-memory for broadcasting.
- Disconnections are handled gracefully without crashing the server.

**Technical Implementation Notes:**
- FastAPI's `@app.websocket("/api/v1/firehose/ws")` and `@app.websocket("/api/v1/chat/ws")`.
- Auth: token passed as query param `?token=...` since WebSocket headers are limited; validated with the same JWT/API key logic from `deps.py`.
- Active connections managed in a `ConnectionManager` class (dict of user_id -> WebSocket).
- `try/except WebSocketDisconnect` ensures clean removal from the manager.

---

### E3-S6: Prometheus Metrics Instrumentation

**Story:** As a Platform Engineer, I want FastAPI automatically instrumented with Prometheus metrics so that request latency, throughput, and error rates are available for dashboarding and alerting.

**Acceptance Criteria:**
- A `/metrics` endpoint exposes Prometheus-formatted metrics.
- Metrics include: request count, request latency histogram (by method, path, status code), and active request gauge.
- Custom application counters (cache hits, rate limit hits) are also exposed.

**Technical Implementation Notes:**
- `prometheus-fastapi-instrumentator` provides zero-config HTTP metrics. Initialized in the lifespan and called with `.instrument(app).expose(app, endpoint="/metrics")`.
- Custom metrics use `prometheus_client` directly: `Counter`, `Histogram`, `Gauge` objects defined in `src/shared/metrics.py` and imported where needed.

---

### E3-S7: Sentry Error & Performance Tracking

**Story:** As a Platform Engineer, I want unhandled exceptions and slow transactions captured in Sentry so that errors are triaged and performance regressions detected early.

**Acceptance Criteria:**
- Unhandled exceptions in any endpoint are reported to Sentry with full stack trace, request context, and user info.
- Performance traces (transactions) are sampled at a configurable rate.
- Sentry breadcrumbs capture database queries and Redis commands.
- Sentry is not initialized when the DSN is empty.

**Technical Implementation Notes:**
- `sentry_sdk.init(dsn=settings.sentry_dsn, integrations=[FastApiIntegration(), SqlalchemyIntegration()], traces_sample_rate=settings.sentry_traces_rate, environment=settings.environment)`.
- Called in the FastAPI lifespan. `before_send` callback strips sensitive headers.
- `settings.sentry_traces_rate` defaults to `0.1` (10% of transactions).

---

## Epic 4: Data Models & Persistence

### E4-S1: User Model Extension

**Story:** As a Platform Engineer, I want the User model to include authentication and profile fields so that registration, login, and role-based access are supported.

**Acceptance Criteria:**
- The `users` table includes: `id` (UUID PK), `email` (unique, indexed), `hashed_password`, `display_name`, `role` (enum: consumer/enterprise/admin), `is_active`, `created_at`, `updated_at`.
- An Alembic migration creates or alters the table.

**Technical Implementation Notes:**
- `src/shared/database/postgres/models/user.py` extends the existing `User(Base, IdMixin, TimestampMixin)` with new columns.
- `role` uses SQLAlchemy `Enum` type mapped to a Python `enum.Enum`.
- Index on `email` for login lookups.

---

### E4-S2: Subscription Model

**Story:** As a Platform Engineer, I want a Subscription model so that user tiers and their expiry can be tracked for feature gating and rate limiting.

**Acceptance Criteria:**
- The `subscriptions` table includes: `id`, `user_id` (FK to users), `tier` (enum: free/pro/enterprise), `started_at`, `expires_at`, `created_at`, `updated_at`.
- A user has at most one active subscription (unique constraint on `user_id` where `expires_at > now()` or `expires_at IS NULL`).

**Technical Implementation Notes:**
- `src/shared/database/postgres/models/subscription.py`. Relationship: `User.subscription` (one-to-one, lazy async select).
- Default tier is `free`, created on user registration.

---

### E4-S3: Article & Source Models

**Story:** As a Platform Engineer, I want Article and Source models so that ingested news metadata and scraped content are persisted with full provenance.

**Acceptance Criteria:**
- `sources` table: `id`, `name`, `url`, `feed_type` (rss/api), `is_active`, `created_at`.
- `articles` table: `id`, `source_id` (FK), `headline`, `url` (unique), `published_at`, `raw_metadata` (JSONB), `created_at`.
- Indexes on `articles.url` (unique) and `articles.published_at` for time-range queries.

**Technical Implementation Notes:**
- `src/shared/database/postgres/models/article.py` and `source.py`.
- `raw_metadata` is a JSONB column storing the full RSS/API entry for auditability.
- Bulk insert via `insert(...).on_conflict_do_nothing(index_elements=["url"])` for idempotent ingestion.

---

### E4-S4: Event Cluster Model

**Story:** As a Platform Engineer, I want an EventCluster model so that grouped news events (the output of HDBSCAN clustering) are tracked with their aggregated summaries and debate outputs.

**Acceptance Criteria:**
- `event_clusters` table: `id`, `label` (human-readable topic), `article_count`, `summary_text`, `debiased_summary`, `sentiment_ratio` (JSONB: `{positive, negative, neutral}`), `ner_tags` (JSONB array), `source_urls` (JSONB array), `embedding_id` (Qdrant point ID), `status` (enum: pending/processing/completed/failed), `created_at`, `updated_at`.
- Relationship: many-to-many with `articles` via a join table `cluster_articles`.

**Technical Implementation Notes:**
- `src/shared/database/postgres/models/event_cluster.py`.
- `cluster_articles` association table: `cluster_id` (FK), `article_id` (FK), composite PK.
- `status` tracks pipeline progress; updated by the ingestion worker.
- `embedding_id` references the Qdrant point for semantic search.

---

### E4-S5: Watchlist Model

**Story:** As a Platform Engineer, I want a Watchlist model so that users' subscribed tickers and topics are persisted for alert matching.

**Acceptance Criteria:**
- `watchlists` table: `id`, `user_id` (FK), `entity_type` (enum: ticker/topic/entity), `entity_value` (e.g., "AAPL", "Federal Reserve"), `alert_threshold` (optional float), `is_active`, `created_at`.
- Composite unique constraint on `(user_id, entity_type, entity_value)`.

**Technical Implementation Notes:**
- `src/shared/database/postgres/models/watchlist.py`.
- `alert_threshold` stores user-defined sensitivity (e.g., "alert if sentiment drops below -0.5"); nullable for simple subscriptions.
- Queried by the alert worker when a new event cluster is finalized: `SELECT * FROM watchlists WHERE entity_value = ANY(:ner_tags)`.

---

### E4-S6: LLM Usage Log Model

**Story:** As a Platform Engineer, I want an LLM usage log table so that every LLM invocation is recorded for cost tracking, billing, and debugging.

**Acceptance Criteria:**
- `llm_usage_log` table: `id`, `provider` (ollama/openai/anthropic), `model_name`, `agent_name` (e.g., "map_extractor", "debate_judge", "rag_chat"), `prompt_tokens`, `completion_tokens`, `total_cost_usd` (nullable, computed), `latency_ms`, `cluster_id` (nullable FK), `user_id` (nullable FK), `created_at`.
- Indexes on `created_at`, `agent_name`, and `provider` for aggregation queries.

**Technical Implementation Notes:**
- `src/shared/database/postgres/models/llm_usage_log.py`.
- Written asynchronously by the `TokenTrackingHandler` callback (see Cross-Cutting Concern).
- `total_cost_usd` computed from a cost-per-token lookup table in config (e.g., gpt-4o: $5/1M input tokens); `NULL` for Ollama (free).
- Admin dashboard queries this table for cost reports grouped by provider/model/agent/day.

---

### E4-S7: API Key Model

**Story:** As a Platform Engineer, I want an API Key model so that enterprise clients' programmatic credentials are stored securely.

**Acceptance Criteria:**
- `api_keys` table: `id`, `user_id` (FK), `hashed_key`, `label`, `is_active`, `last_used_at`, `created_at`.
- Only the SHA-256 hash of the key is stored; the raw key is returned once on creation.

**Technical Implementation Notes:**
- `src/shared/database/postgres/models/api_key.py`.
- Lookup: hash the incoming `X-API-Key` header value and `SELECT` by `hashed_key` where `is_active = true`.
- `last_used_at` updated on each successful authentication (debounced to avoid write amplification: only update if >1 minute since last update).

---

### E4-S8: Qdrant Collection Setup

**Story:** As a Platform Engineer, I want Qdrant collections defined for news embeddings and private RAG documents so that semantic search is ready for both B2C and B2B workloads.

**Acceptance Criteria:**
- A `news_embeddings` collection exists with vector size matching the embedding model (e.g., 1536 for OpenAI `text-embedding-3-small` or 768 for a local model).
- Private RAG collections follow the naming convention `rag_{tenant_id}` and are created on-demand when an enterprise client uploads their first document.
- Collection creation is idempotent (no error if already exists).

**Technical Implementation Notes:**
- `src/shared/qdrant/client.py` wraps `qdrant_client.AsyncQdrantClient`.
- On app startup, `ensure_collection("news_embeddings", vector_size=settings.embedding_dim)` is called.
- `ensure_collection` calls `get_collection` and creates if not found, with cosine distance metric.
- Tenant-specific collections created by the RAG ingest worker.

---

### E4-S9: MinIO Bucket Structure

**Story:** As a Platform Engineer, I want MinIO buckets pre-created for different asset types so that object storage is organized from the start.

**Acceptance Criteria:**
- Buckets exist: `prism-images`, `prism-pdfs`, `prism-filings` (SEC/Edgar), `prism-rag-uploads`.
- Bucket creation is idempotent and runs on app startup.
- Objects are stored with a structured key pattern: `{bucket}/{year}/{month}/{day}/{uuid}.{ext}`.

**Technical Implementation Notes:**
- `src/shared/minio/client.py` wraps the `miniio` async client. `ensure_bucket(name)` checks existence and creates if needed.
- Called during FastAPI lifespan startup for the four predefined buckets.
- The RAG ingest worker stores uploaded enterprise documents in `prism-rag-uploads/{tenant_id}/{uuid}.pdf`.

---

## Epic 5: Agentic Ingestion Pipeline

### E5-S1: RSS Metadata Scraping DAG

**Story:** As a Platform Engineer, I want an Airflow DAG that scrapes RSS feed metadata on a schedule so that new headlines are continuously ingested into the system.

**Acceptance Criteria:**
- The DAG runs every 15 minutes.
- It iterates over a configurable list of RSS feed URLs (stored in an Airflow Variable or config file).
- For each feed, it extracts: headline, source name, article URL, and published timestamp.
- Extracted metadata is bulk-inserted into the `articles` table (idempotent on URL).
- DAG logs the count of new vs. duplicate articles per run.

**Technical Implementation Notes:**
- `dags/ingest_rss_metadata.py` using `@dag` and `@task` decorators (TaskFlow API).
- Uses `feedparser` to parse RSS XML. Each feed is processed as a mapped task for parallelism.
- Bulk insert via SQLAlchemy `insert().on_conflict_do_nothing(index_elements=["url"])` using a sync Postgres connection (Airflow's default executor).
- Source list stored as an Airflow Variable `rss_feed_urls` (JSON array).

---

### E5-S2: Headline Vectorization & HDBSCAN Clustering

**Story:** As a Platform Engineer, I want new headlines vectorized and clustered so that related articles about the same event are grouped before deep processing.

**Acceptance Criteria:**
- A downstream Airflow task (or a separate DAG triggered after ingestion) fetches un-clustered articles from the last N hours.
- Headlines are embedded using the configured embedding model (via the LLM factory, supporting Ollama or cloud).
- HDBSCAN clusters the vectors; each cluster represents a distinct news event.
- Cluster assignments are written back to the `cluster_articles` join table and new `event_clusters` rows are created with status `pending`.
- Singleton articles (noise in HDBSCAN) are either assigned to a single-article cluster or skipped based on config.

**Technical Implementation Notes:**
- `dags/cluster_headlines.py`. Triggered by `ingest_rss_metadata` via `TriggerDagRunOperator` or a sensor.
- Embedding: calls the LLM factory's embedding function (LangChain `Embeddings` interface — `OllamaEmbeddings` or `OpenAIEmbeddings`).
- `hdbscan` Python library with configurable `min_cluster_size` and `min_samples` (stored as Airflow Variables for admin tuning per E10-S6).
- Writes to PostgreSQL: creates `event_clusters` rows and `cluster_articles` associations.

---

### E5-S3: RabbitMQ Event Cluster Queuing

**Story:** As a Platform Engineer, I want completed clusters enqueued to RabbitMQ so that the Tier 2 LangGraph workers can process them asynchronously and independently of Airflow.

**Acceptance Criteria:**
- After clustering, each new `event_cluster` (status: `pending`) is published as a message to the `cluster_processing` RabbitMQ queue.
- The message payload contains the `cluster_id` and a list of `article_ids`.
- Messages are persistent (survive broker restart).
- Publishing is idempotent: re-running the task does not create duplicate messages for already-queued clusters.

**Technical Implementation Notes:**
- Published from the Airflow clustering task using `aio-pika` (or `pika` sync client within the Airflow task).
- RabbitMQ queue `cluster_processing` declared as durable with `x-message-ttl` for safety.
- The `event_cluster.status` is updated to `processing` after successful publish, preventing re-queue on DAG retry.

---

### E5-S4: LangGraph MapReduce — Map Phase (Parallel Fact Extraction)

**Story:** As a Platform Engineer, I want each article in a cluster processed in parallel by a LangGraph Map node so that atomic facts and named entities are extracted quickly using a fast, small LLM.

**Acceptance Criteria:**
- The ingestion worker receives a cluster message from RabbitMQ and instantiates a LangGraph `StateGraph`.
- The Map phase uses LangGraph's `Send()` API to dynamically spawn one node per article in the cluster.
- Each Map node calls a fast LLM (e.g., Ollama `llama3` or a small cloud model) with a structured extraction prompt.
- Output per article: a JSON object with `facts` (list of atomic statements), `entities` (NER: persons, orgs, tickers, locations), and `sentiment` (positive/negative/neutral).
- All Map outputs are collected into the graph state.

**Technical Implementation Notes:**
- `ai/graphs/map_reduce.py` defines the `StateGraph` with `TypedDict` state.
- `Send()` dispatches to a `map_extract` node for each article. The node calls `ChatOllama` or `ChatOpenAI` (resolved by the LLM factory in `ai/llm/factory.py` using per-role config `LLM_MAP_PROVIDER`/`LLM_MAP_MODEL`).
- Prompt template in `ai/prompts/map_extract.py` instructs structured JSON output. LangChain's `PydanticOutputParser` or `JsonOutputParser` validates the response.
- `TokenTrackingHandler` callback attached to every LLM call; records prompt/completion tokens to Prometheus and `llm_usage_log`.
- LangSmith/Langfuse tracing captures each Map node's input/output automatically.

---

### E5-S5: LangGraph MapReduce — Reduce Phase (State Merging)

**Story:** As a Platform Engineer, I want the Map outputs aggregated by a Reduce node so that duplicate facts are removed and conflicting data points are explicitly flagged.

**Acceptance Criteria:**
- LangGraph's state reducer (using `Annotated[list, operator.add]`) collects all Map outputs into a single list in the graph state.
- The Reduce node deduplicates facts by semantic similarity (exact match or embedding cosine > threshold).
- Conflicting data points (e.g., "CEO resigned" from source A vs. "CEO denied resignation" from source B) are flagged with both source attributions.
- Output: a `ReducedState` containing `unique_facts`, `conflicts`, `merged_entities`, and `sentiment_counts`.

**Technical Implementation Notes:**
- `ai/graphs/map_reduce.py` Reduce node. State uses `Annotated` type hints with custom reducer functions.
- Deduplication: compute pairwise similarity on fact strings (embedding-based or fuzzy string matching via `rapidfuzz`). Facts above threshold are merged; the source with more corroboration is kept as primary.
- Conflicts: facts with contradictory predicates about the same entity are grouped into a `conflicts` list with source URLs.
- Sentiment counts: simple aggregation of per-article sentiment labels.

---

### E5-S6: Multi-Agent Debate Subgraph

**Story:** As a Platform Engineer, I want a Multi-Agent Debate (Proponent, Skeptic, Judge) to synthesize the reduced facts into a debiased summary so that the final output reflects balanced, critically examined information.

**Acceptance Criteria:**
- The Debate is a LangGraph subgraph invoked after the Reduce phase.
- The **Proponent Agent** receives the reduced state and writes a narrative highlighting mainstream implications and consensus facts.
- The **Skeptic Agent** receives the Proponent's narrative plus the `conflicts` list and fringe facts; it writes a counter-narrative challenging unsupported claims.
- The **Judge Agent** receives the full graph state history (Proponent output, Skeptic output, original reduced facts) and writes the final debiased Prism summary.
- The Judge's output includes: `debiased_summary` (text), `confidence_score` (0-1), and `sources_cited` (list of URLs).

**Technical Implementation Notes:**
- `ai/graphs/debate.py` defines a subgraph with three sequential nodes: `proponent`, `skeptic`, `judge`.
- Each node uses the LLM factory with role-specific config (e.g., `LLM_PROPONENT_PROVIDER`, `LLM_JUDGE_PROVIDER`), allowing the Judge to use a more capable model.
- Prompt templates in `ai/prompts/proponent.py`, `skeptic.py`, `judge.py`.
- The full state history is passed to the Judge by including prior node outputs in the `TypedDict` state.
- All three nodes are traced in LangSmith/Langfuse; the trace shows the full Proponent → Skeptic → Judge flow for debugging.
- `TokenTrackingHandler` records tokens per agent for cost attribution.

---

### E5-S7: Ingestion Worker (RabbitMQ Consumer)

**Story:** As a Platform Engineer, I want a long-running RabbitMQ consumer process that orchestrates the full MapReduce + Debate pipeline for each cluster so that ingestion runs independently of Airflow.

**Acceptance Criteria:**
- The worker connects to RabbitMQ and consumes from the `cluster_processing` queue.
- For each message, it runs the full LangGraph pipeline (Map → Reduce → Debate).
- On success: updates the `event_clusters` row with `debiased_summary`, `ner_tags`, `sentiment_ratio`, `source_urls`, and sets status to `completed`. Saves the embedding to Qdrant.
- On failure: sets status to `failed`, logs the error to Sentry, and nacks the message for retry (up to 3 attempts via dead-letter exchange).
- The worker runs as a standalone Python process (containerizable).

**Technical Implementation Notes:**
- `workers/ingestion_worker/consumer.py` using `aio-pika` for async consumption.
- Calls `ai/graphs/map_reduce.py` compiled graph with the cluster's articles.
- Embeds the final `debiased_summary` using the embedding model and upserts to Qdrant `news_embeddings` collection with metadata (cluster_id, ner_tags, created_at).
- Dead-letter exchange `cluster_processing_dlx` with `x-max-retries=3`.
- Prometheus gauge: `prism_ingestion_worker_active_tasks`.

---

### E5-S8: Pipeline Prometheus Metrics

**Story:** As a Platform Engineer, I want custom Prometheus metrics emitted by the ingestion pipeline so that throughput, cost, and health are observable in Grafana.

**Acceptance Criteria:**
- Counters: `prism_articles_ingested_total`, `prism_clusters_processed_total`, `prism_clusters_failed_total`.
- Histograms: `prism_cluster_processing_duration_seconds`, `prism_llm_call_duration_seconds` (labeled by agent).
- Gauges: `prism_llm_prompt_tokens_total`, `prism_llm_completion_tokens_total` (labeled by model/provider/agent).
- Metrics are exposed via a `/metrics` endpoint on the worker process (using `prometheus_client` start_http_server).

**Technical Implementation Notes:**
- Metrics defined in `src/shared/metrics.py` (shared with FastAPI) and `workers/ingestion_worker/metrics.py`.
- `TokenTrackingHandler` increments the token counters on each LLM call.
- Worker exposes metrics on a configurable port (default 9091) scraped by Prometheus.

---

## Epic 6: B2C — "Discover" Feed & Context

### E6-S1: Daily Feed Endpoint

**Story:** As a Consumer, I want to fetch my daily news feed so that I can read debiased summaries of the latest events.

**Acceptance Criteria:**
- `GET /api/v1/feed` returns a paginated list of recent event clusters (debiased summary, entities, sentiment, source count, timestamp).
- Supports `?page=`, `?page_size=`, and `?since=` (ISO timestamp) query parameters.
- Response is served from Redis cache (TTL: 5 min). Cache miss falls through to PostgreSQL.
- Each feed item includes a list of highlighted entity names (for inline UI highlighting).

**Technical Implementation Notes:**
- `src/api/v1/feed.py` route. Queries `event_clusters` where `status=completed`, ordered by `created_at DESC`.
- Redis cache key: `feed:page:{page}:size:{size}:since:{since}`. Invalidated by the ingestion worker on new cluster completion.
- Response schema: Pydantic model with `id`, `label`, `debiased_summary`, `entities` (list), `sentiment_ratio`, `article_count`, `source_urls`, `created_at`.

---

### E6-S2: Entity Highlighting in Summaries

**Story:** As a Consumer, I want named entities (people, companies, tickers) visually highlighted in the summary text so that I can quickly identify key actors and click for more context.

**Acceptance Criteria:**
- The feed response includes an `entities` array with `name`, `type` (person/org/ticker/location), and `start`/`end` character offsets within the `debiased_summary`.
- The frontend uses these offsets to wrap entities in clickable `<span>` elements.

**Technical Implementation Notes:**
- Entity offsets are computed during the Debate Judge phase: the Judge prompt instructs the LLM to output entity positions, or a post-processing step runs NER (spaCy or regex for tickers) on the `debiased_summary` and matches against the `ner_tags` extracted during Map.
- Stored in the `event_clusters.ner_tags` JSONB column as `[{name, type, start, end}]`.

---

### E6-S3: Historical Context Retrieval (Qdrant Semantic Search)

**Story:** As a Consumer, I want to click on an entity and see historical context (past events involving that entity) so that I understand the broader narrative.

**Acceptance Criteria:**
- `GET /api/v1/context/{entity_name}` returns the top N semantically similar past event clusters involving that entity.
- Results include the debiased summary, date, and similarity score.
- Qdrant is queried with the entity name embedded as a vector, filtered by `ner_tags` containing the entity.

**Technical Implementation Notes:**
- `src/api/v1/feed.py` (or a dedicated `context.py` route).
- Embeds the `entity_name` using the same embedding model as ingestion.
- Qdrant `search` with a payload filter: `must` condition on `ner_tags` containing the entity name, plus vector similarity.
- Results are combined with PostgreSQL data (full summary text, source URLs) by joining on `embedding_id` / `cluster_id`.
- Redis cached with key `context:{entity_name}` (TTL: 30 min).

---

### E6-S4: "Ask Prism" Chat Interface (Backend)

**Story:** As a Consumer, I want to ask free-form questions about the news and get AI-generated answers grounded in Prism's data so that I can explore topics in depth.

**Acceptance Criteria:**
- `POST /api/v1/chat` (or WebSocket `/api/v1/chat/ws`) accepts a user message and returns an AI-generated response.
- Responses cite specific event clusters and source URLs.
- Chat history is maintained per session (last N messages sent as context).
- Token usage per chat turn is tracked and counted against the user's tier quota.

**Technical Implementation Notes:**
- `src/api/v1/chat.py` route invokes the LangGraph RAG agent from `ai/graphs/rag_chat.py`.
- The RAG agent: (1) embeds the user query, (2) searches Qdrant `news_embeddings` for relevant clusters, (3) retrieves full summaries from PostgreSQL, (4) generates a grounded answer via LLM with sources in the prompt.
- Chat history stored in Redis: `chat:{user_id}:{session_id}` as a list of `{role, content}` JSON objects (TTL: 24h).
- `TokenTrackingHandler` logs usage with `agent_name="rag_chat"` and `user_id`.
- Tier quota checked before invocation; 429 if exceeded.

---

## Epic 7: B2C — Watchlists & Alerts

### E7-S1: Watchlist CRUD

**Story:** As a Retail Investor, I want to create, read, update, and delete watchlist entries for tickers and topics so that I receive alerts when relevant news breaks.

**Acceptance Criteria:**
- `POST /api/v1/watchlists` creates a watchlist entry (entity_type, entity_value, optional alert_threshold).
- `GET /api/v1/watchlists` lists the authenticated user's entries.
- `PUT /api/v1/watchlists/{id}` updates threshold or active status.
- `DELETE /api/v1/watchlists/{id}` removes an entry.
- Maximum 50 watchlist entries for Free tier, 200 for Pro, unlimited for Enterprise.

**Technical Implementation Notes:**
- `src/api/v1/watchlists.py` CRUD routes. Standard Pydantic request/response schemas.
- Queries against `watchlists` table filtered by `user_id`.
- Tier limit checked on `POST` by counting existing entries and comparing to subscription tier limits.

---

### E7-S2: Alert Matching & Delivery

**Story:** As a Retail Investor, I want to be notified when a news event matches my watchlist entries so that I can react to market-moving information quickly.

**Acceptance Criteria:**
- When the ingestion worker finalizes a cluster, it checks whether any `ner_tags` match active watchlist entries.
- If a match is found and the cluster's sentiment exceeds the user's `alert_threshold` (if set), an alert is enqueued.
- Alerts are delivered via a push notification endpoint (or email placeholder).
- The user can view past alerts via `GET /api/v1/alerts`.

**Technical Implementation Notes:**
- After cluster completion, the ingestion worker publishes to the `alert_matching` RabbitMQ queue with `cluster_id` and `ner_tags`.
- `workers/alert_worker/consumer.py` consumes and queries PostgreSQL: `SELECT * FROM watchlists WHERE entity_value = ANY(:tags) AND is_active = true`.
- For each match, creates an `alerts` row in PostgreSQL (`id`, `user_id`, `cluster_id`, `entity_matched`, `delivered_at`, `created_at`) and pushes via the notification channel.
- Initial notification: in-app (fetched by frontend polling `GET /api/v1/alerts?unread=true`). Email/push can be added later.

---

## Epic 8: B2B — Firehose API

### E8-S1: WebSocket Firehose Stream

**Story:** As an Enterprise Client (algorithmic trading firm), I want a real-time WebSocket stream of structured event data so that my trading systems can ingest sentiment and fact data as soon as it is produced.

**Acceptance Criteria:**
- `WS /api/v1/firehose/ws` accepts a connection authenticated via API key (query param).
- As each cluster completes processing, the structured JSON (debiased summary, sentiment ratio, NER tags, source URLs, fact count) is pushed to all connected firehose clients.
- Clients can optionally filter by entity/ticker via a subscribe message after connection.
- The stream includes a `sequence_id` for gap detection.

**Technical Implementation Notes:**
- `src/api/v1/firehose_ws.py` WebSocket endpoint.
- Authentication: `?api_key=...` validated against the `api_keys` table via `get_current_user_or_api_key`.
- `ConnectionManager` in `src/api/v1/firehose_ws.py` maintains active connections and optional per-connection filters.
- The ingestion worker, after completing a cluster, publishes a Redis `PUBLISH` on channel `firehose:new_cluster`. The FastAPI process subscribes and broadcasts to connected WebSocket clients.
- `sequence_id`: auto-incrementing Redis counter `firehose:seq`.

---

### E8-S2: Firehose Sentiment Ratio Delivery

**Story:** As an Enterprise Client, I want each firehose event to include the sentiment ratio (positive/negative/neutral article counts) so that my systems can factor market sentiment into trading signals.

**Acceptance Criteria:**
- Each firehose message includes a `sentiment_ratio` object: `{positive: int, negative: int, neutral: int, score: float}`.
- The `score` is a normalized value: `(positive - negative) / total`.
- Historical sentiment data is queryable via `GET /api/v1/firehose/sentiment?entity=AAPL&since=...` for backtesting.

**Technical Implementation Notes:**
- `sentiment_ratio` is computed during the Reduce phase and stored on the `event_clusters` row.
- The REST endpoint queries PostgreSQL with entity filter (via `ner_tags` JSONB containment) and time range.
- Redis cached for frequently queried tickers (TTL: 1 min).

---

## Epic 9: B2B — Private RAG Workspace

### E9-S1: Enterprise Document Upload

**Story:** As an Enterprise Client, I want to upload internal documents (PDFs, reports) to a secure workspace so that my team can query them alongside global news.

**Acceptance Criteria:**
- `POST /api/v1/rag/upload` accepts a multipart file upload (PDF, DOCX, TXT; max 50MB).
- The file is streamed to MinIO bucket `prism-rag-uploads/{tenant_id}/{uuid}.{ext}`.
- A processing job is enqueued to RabbitMQ queue `rag_ingest`.
- Upload status is returned immediately (202 Accepted) with a `document_id` for polling.
- `GET /api/v1/rag/documents` lists the tenant's uploaded documents with processing status.

**Technical Implementation Notes:**
- `src/api/v1/rag_workspace.py` route. Uses FastAPI `UploadFile` with streaming to MinIO via the async MinIO client.
- `Document` model in PostgreSQL: `id`, `tenant_id` (user_id for enterprise user), `filename`, `minio_key`, `status` (uploading/processing/ready/failed), `page_count`, `created_at`.
- RabbitMQ message: `{document_id, tenant_id, minio_key}`.

---

### E9-S2: Document Processing Worker (OCR, Chunk, Embed)

**Story:** As a Platform Engineer, I want uploaded documents automatically parsed, chunked, and embedded so that they are searchable in the enterprise's private Qdrant collection.

**Acceptance Criteria:**
- The RAG ingest worker downloads the file from MinIO, parses it (OCR for scanned PDFs), splits into chunks, embeds each chunk, and upserts to the tenant's private Qdrant collection.
- Chunk size is configurable (default: 512 tokens with 64 token overlap).
- Each Qdrant point stores metadata: `document_id`, `chunk_index`, `page_number`, `text_preview`.
- Document status is updated to `ready` on success or `failed` on error.

**Technical Implementation Notes:**
- `workers/rag_ingest_worker/consumer.py` consumes from `rag_ingest` queue.
- Uses LangChain document loaders: `PyPDFLoader`, `UnstructuredWordDocumentLoader`, with `Tesseract` OCR fallback for scanned pages.
- `RecursiveCharacterTextSplitter` with `chunk_size=512`, `chunk_overlap=64`.
- Embedding via the LLM factory's embedding interface.
- Qdrant collection: `rag_{tenant_id}`, created on first upload via `ensure_collection`.
- Token usage tracked with `agent_name="rag_embedder"` and `user_id=tenant_id`.

---

### E9-S3: Private RAG Chat (Cross-Reference)

**Story:** As an Enterprise Client, I want a chat interface that answers questions by cross-referencing my private documents with global Prism news so that I get intelligence enriched with my proprietary data.

**Acceptance Criteria:**
- `POST /api/v1/rag/chat` accepts a message and returns an AI-generated answer.
- The RAG agent searches both the tenant's private Qdrant collection and the global `news_embeddings` collection.
- Responses clearly attribute which information came from private documents vs. global news.
- Token usage is tracked per tenant for billing.

**Technical Implementation Notes:**
- `src/api/v1/rag_workspace.py` chat route invokes `ai/graphs/rag_chat.py` with an additional `collections` parameter: `["rag_{tenant_id}", "news_embeddings"]`.
- The RAG agent performs parallel Qdrant searches across both collections, merges results by relevance, and generates a grounded response.
- Source attribution: each retrieved chunk is tagged with `source_type: "private" | "global"` before being passed to the LLM prompt.
- `TokenTrackingHandler` logs with `agent_name="rag_chat_enterprise"` and `user_id=tenant_id` for per-tenant cost tracking.

---

## Epic 10: Admin — Observability & Pipeline Management

### E10-S1: Admin Dashboard API

**Story:** As a System Administrator, I want a set of API endpoints that aggregate system health metrics so that the admin portal can render a real-time dashboard.

**Acceptance Criteria:**
- `GET /api/v1/admin/health` returns status of all services (Postgres, Redis, RabbitMQ, Qdrant, MinIO, Airflow).
- `GET /api/v1/admin/stats` returns high-level stats: total users, clusters processed today, articles ingested, active WebSocket connections.
- All admin endpoints require `admin` role.

**Technical Implementation Notes:**
- `src/api/v1/admin.py` routes.
- Health checks: Postgres `ping()`, Redis `PING`, RabbitMQ management API `/api/health/checks/alarms`, Qdrant `/healthz`, MinIO `list_buckets`, Airflow `/health`.
- Stats: SQL aggregation queries on `event_clusters`, `articles`, `users` tables. WebSocket count from `ConnectionManager`.
- Redis cached (TTL: 30s) to avoid hammering dependencies on every admin page load.

---

### E10-S2: Airflow Health & DAG Management

**Story:** As a System Administrator, I want to view Airflow DAG statuses and manually trigger or retry failed DAGs from the admin portal so that pipeline issues can be resolved without accessing Airflow directly.

**Acceptance Criteria:**
- `GET /api/v1/admin/airflow/dags` returns a list of DAGs with last run status, next scheduled run, and success/failure counts.
- `POST /api/v1/admin/airflow/dags/{dag_id}/trigger` triggers a DAG run.
- `POST /api/v1/admin/airflow/dags/{dag_id}/runs/{run_id}/retry` retries a failed DAG run.

**Technical Implementation Notes:**
- Proxies to the Airflow REST API (`/api/v1/dags`, `/api/v1/dags/{dag_id}/dagRuns`). FastAPI acts as a gateway with admin auth.
- Airflow REST API base URL from `settings.airflow_api_url` (default `http://airflow-webserver:8080/api/v1`).
- Authentication to Airflow via basic auth with admin credentials from settings.

---

### E10-S3: RabbitMQ Queue Monitoring

**Story:** As a System Administrator, I want to see RabbitMQ queue depths and consumer counts so that I can detect processing backlogs.

**Acceptance Criteria:**
- `GET /api/v1/admin/queues` returns queue names, message counts (ready, unacknowledged), and consumer counts.
- Alerting thresholds are configurable; the endpoint flags queues exceeding their threshold.

**Technical Implementation Notes:**
- Proxies to the RabbitMQ Management HTTP API (`/api/queues`).
- `settings.rabbitmq_management_url` defaults to `http://rabbitmq:15672`.
- Threshold config stored as an Airflow Variable or in PostgreSQL `admin_config` table.

---

### E10-S4: LangGraph Trace & Cost Reporting

**Story:** As a System Administrator, I want to view LLM usage reports (tokens in/out, cost, latency) broken down by model, provider, and agent so that I can optimize spend and performance.

**Acceptance Criteria:**
- `GET /api/v1/admin/llm/usage` returns aggregated LLM usage data with filters: date range, provider, model, agent.
- Response includes: total prompt tokens, total completion tokens, estimated cost (USD), average latency, call count.
- `GET /api/v1/admin/llm/traces/{cluster_id}` returns a link to the LangSmith/Langfuse trace for a specific pipeline run.

**Technical Implementation Notes:**
- Queries the `llm_usage_log` PostgreSQL table with `GROUP BY` on requested dimensions.
- Cost computed by joining against a `llm_pricing` config (stored in settings or a small table): cost per 1M input/output tokens per model.
- Trace link: the `llm_usage_log` stores a `trace_id` (from LangSmith/Langfuse callback); the endpoint constructs the URL from `settings.langfuse_host` or `https://smith.langchain.com`.

---

### E10-S5: Manual DAG Re-Trigger

**Story:** As a System Administrator, I want to re-trigger a failed ingestion run for a specific cluster so that transient errors (LLM timeout, network issue) can be recovered without re-running the entire pipeline.

**Acceptance Criteria:**
- `POST /api/v1/admin/clusters/{cluster_id}/reprocess` re-enqueues the cluster to the `cluster_processing` RabbitMQ queue.
- The cluster's status is reset to `pending`.
- The admin can optionally override LLM provider/model for the retry (e.g., switch from Ollama to cloud).

**Technical Implementation Notes:**
- `src/api/v1/admin.py` route. Updates `event_clusters.status` to `pending`, publishes the message to RabbitMQ.
- Optional override: the message payload includes `llm_overrides: {map_provider, map_model, judge_provider, judge_model}` which the ingestion worker reads and passes to the LLM factory.

---

### E10-S6: HDBSCAN Parameter Tuning

**Story:** As a System Administrator, I want to adjust HDBSCAN clustering parameters (min_cluster_size, min_samples) from the admin portal so that clustering quality can be tuned without code deployments.

**Acceptance Criteria:**
- `GET /api/v1/admin/pipeline/config` returns current clustering parameters.
- `PUT /api/v1/admin/pipeline/config` updates parameters.
- Changes take effect on the next Airflow DAG run without restart.

**Technical Implementation Notes:**
- Parameters stored as Airflow Variables (`hdbscan_min_cluster_size`, `hdbscan_min_samples`).
- The admin endpoint proxies to the Airflow Variables API (`/api/v1/variables`).
- The clustering DAG reads these variables at runtime.

---

## Epic 11: Frontend Application (React + Redux)

### E11-S1: Application Shell & Routing

**Story:** As a Consumer, I want a fast-loading single-page application with intuitive navigation so that I can quickly access the feed, chat, and my watchlist.

**Acceptance Criteria:**
- The React app loads with a responsive layout: top nav bar, main content area, and collapsible sidebar.
- Routes: `/` (feed), `/chat` (Ask Prism), `/watchlist`, `/settings`, `/login`, `/register`.
- Enterprise routes: `/workspace` (private RAG). Admin routes: `/admin`.
- Protected routes redirect to `/login` if unauthenticated.
- Dynamic page titles and meta tags via React Helmet for SEO.

**Technical Implementation Notes:**
- `frontend/src/app/App.tsx` with `react-router-dom` for routing.
- `frontend/src/app/routes.tsx` defines route config with `lazy()` for code splitting.
- Helmet in each page component sets `<title>` and `<meta>` tags.
- Auth guard component checks Redux `userAuthSlice.isAuthenticated` and redirects.
- Tailwind CSS for responsive design; mobile-first breakpoints.

---

### E11-S2: Redux Store Architecture

**Story:** As a Platform Engineer, I want a well-structured Redux store so that global state (auth, feed, sidebar, chat) is managed predictably without prop drilling.

**Acceptance Criteria:**
- Redux Toolkit store with slices: `userAuthSlice`, `feedSlice`, `sidebarContextSlice`, `chatSlice`, `watchlistSlice`.
- Each slice has typed state, reducers, and async thunks for API calls.
- RTK Query (optional) or `createAsyncThunk` handles API requests with loading/error states.

**Technical Implementation Notes:**
- `frontend/src/app/store.ts` configures the store with `configureStore`.
- `frontend/src/features/` contains one folder per slice: `feed/feedSlice.ts`, `auth/userAuthSlice.ts`, etc.
- Async thunks use `fetch` or `axios` to call the FastAPI backend.
- `userAuthSlice` stores JWT, user profile, and tier. Token persisted in `localStorage` and rehydrated on app load.

---

### E11-S3: Feed Rendering

**Story:** As a Consumer, I want the feed displayed as a scrollable list of news cards so that I can scan headlines and summaries at a glance.

**Acceptance Criteria:**
- Each card shows: event label, debiased summary (truncated), entity tags as pills, sentiment indicator, source count, and relative timestamp.
- Infinite scroll or "Load More" pagination.
- Skeleton loading state while data is fetched.
- Pull-to-refresh on mobile.

**Technical Implementation Notes:**
- `frontend/src/features/feed/FeedPage.tsx` dispatches `fetchFeed` thunk on mount.
- `frontend/src/components/EventCard.tsx` renders a single cluster.
- Entity pills are `<span>` elements with `onClick` handlers that dispatch `loadEntityContext`.
- Tailwind: card layout with hover state, responsive grid (1 col mobile, 2 col tablet, 3 col desktop).

---

### E11-S4: Entity-Click Sidebar Interaction

**Story:** As a Consumer, I want to click on a highlighted entity in a summary and see a sidebar with historical context so that I can understand the entity's news trajectory without leaving the feed.

**Acceptance Criteria:**
- Clicking an entity pill dispatches a Redux action to `sidebarContextSlice`.
- The sidebar slides in from the right with a loading spinner.
- The sidebar displays: entity name, type, and a chronological list of past event summaries involving that entity (from Qdrant semantic search).
- Clicking outside the sidebar or pressing Escape closes it.

**Technical Implementation Notes:**
- `frontend/src/features/sidebar/SidebarContext.tsx` reads from `sidebarContextSlice`.
- The thunk `loadEntityContext(entityName)` calls `GET /api/v1/context/{entity_name}` and stores results in the slice.
- CSS: `transform: translateX(100%)` to `translateX(0)` with transition for slide animation. Tailwind `translate-x-full` / `translate-x-0`.
- Backdrop overlay with `onClick` to close.

---

### E11-S5: Chat Interface ("Ask Prism")

**Story:** As a Consumer, I want a chat interface where I can ask questions about the news and receive AI-generated, source-cited answers so that I can do deep-dive research.

**Acceptance Criteria:**
- The chat page shows a message history (user messages and AI responses).
- User can type a message and press Enter or click Send.
- AI responses include inline source citations (clickable links).
- Chat history persists across page navigations within the same session.
- Loading indicator while the AI generates a response.
- Tier quota warning shown when approaching the limit.

**Technical Implementation Notes:**
- `frontend/src/features/chat/ChatPage.tsx` and `chatSlice.ts`.
- Messages stored in Redux: `chatSlice.messages: [{role, content, sources?}]`.
- Sends via `POST /api/v1/chat` (or WebSocket for streaming). If WebSocket: partial tokens streamed and appended to the current AI message in Redux.
- Source citations rendered as `<a>` tags with Tailwind styling.
- Quota: `chatSlice.remainingQuota` decremented locally and synced from the backend.

---

### E11-S6: Watchlist Management UI

**Story:** As a Retail Investor, I want a page to manage my watchlist (add/remove tickers, set alert thresholds) so that I control what notifications I receive.

**Acceptance Criteria:**
- The watchlist page lists all entries with entity name, type, threshold, and active toggle.
- "Add to Watchlist" form with autocomplete for entity names (sourced from known NER tags).
- Edit threshold inline.
- Delete with confirmation.
- Unread alerts shown as a badge on the watchlist nav item.

**Technical Implementation Notes:**
- `frontend/src/features/watchlist/WatchlistPage.tsx` and `watchlistSlice.ts`.
- CRUD thunks call `/api/v1/watchlists` endpoints.
- Autocomplete: `GET /api/v1/entities/search?q=...` endpoint that queries distinct `ner_tags` from `event_clusters`.
- Alert badge: polls `GET /api/v1/alerts?unread=true&count_only=true` every 60 seconds (or WebSocket push).

---

### E11-S7: B2B Workspace UI

**Story:** As an Enterprise Client, I want a workspace page to upload documents and chat with my private data so that my team can leverage Prism's AI on proprietary information.

**Acceptance Criteria:**
- Document upload area with drag-and-drop and progress bar.
- Document list showing filename, status (processing/ready/failed), page count, and upload date.
- Chat interface scoped to the private workspace (same UX as "Ask Prism" but queries private + global data).
- Responses visually differentiate private vs. global sources.

**Technical Implementation Notes:**
- `frontend/src/pages/WorkspacePage.tsx`.
- Upload: `POST /api/v1/rag/upload` with `FormData`. Progress tracked via `XMLHttpRequest` `onprogress` or `axios` progress callback.
- Document list: polls `GET /api/v1/rag/documents` or uses WebSocket for status updates.
- Chat: reuses `ChatPage` component with a `workspace=true` prop that routes to `POST /api/v1/rag/chat`.
- Source cards tagged with a "Private" or "Global" badge.

---

### E11-S8: Admin Portal UI

**Story:** As a System Administrator, I want an admin portal within the frontend so that I can monitor system health, view pipeline metrics, and manage the platform without switching tools.

**Acceptance Criteria:**
- Admin page accessible only to `admin` role (route guard).
- Sections: System Health, Pipeline Status, LLM Usage/Cost, Queue Depths, User Management.
- System Health: green/red status for each service.
- Pipeline Status: recent clusters with status, processing time, and link to trace.
- LLM Usage: table and chart of token usage over time, filterable by model/provider/agent.

**Technical Implementation Notes:**
- `frontend/src/pages/AdminPage.tsx` with tab navigation for sub-sections.
- Calls `GET /api/v1/admin/health`, `GET /api/v1/admin/stats`, `GET /api/v1/admin/llm/usage`, `GET /api/v1/admin/queues`.
- Charts rendered with a lightweight library (e.g., `recharts` or `chart.js`).
- Embeds Grafana dashboard panels via `<iframe>` for detailed metrics (Grafana configured to allow embedding).

---

### E11-S9: Sentry Browser SDK Integration

**Story:** As a Platform Engineer, I want frontend JavaScript errors and performance data captured in Sentry so that client-side issues are detected and diagnosed.

**Acceptance Criteria:**
- `Sentry.init()` is called on app load with the frontend DSN, environment, and release.
- Unhandled exceptions and promise rejections are reported automatically.
- Performance traces are captured for page navigations and API calls.
- Session replay is enabled at a low sample rate for debugging UX issues.
- Sentry is not initialized if the DSN env var is empty.

**Technical Implementation Notes:**
- `frontend/src/app/sentry.ts` initializes `@sentry/react` with `BrowserTracing` and `Replay` integrations.
- `Sentry.ErrorBoundary` wraps the app root for React error boundaries.
- Release set from `REACT_APP_SENTRY_RELEASE` (injected at build time).
- `replaysSessionSampleRate: 0.1`, `replaysOnErrorSampleRate: 1.0`.

---

## Epic 12: Observability & Monitoring

### E12-S1: Prometheus Scrape Configuration

**Story:** As a Platform Engineer, I want Prometheus configured to scrape all application and infrastructure metrics so that a unified time-series store is available for dashboarding and alerting.

**Acceptance Criteria:**
- `prometheus.yml` defines scrape jobs for: FastAPI `/metrics`, ingestion worker `/metrics`, postgres_exporter, redis_exporter, RabbitMQ `/api/metrics`, Airflow StatsD exporter.
- Scrape interval: 15s for application metrics, 30s for infrastructure exporters.
- Prometheus starts and shows all targets as "UP" in the Targets page.

**Technical Implementation Notes:**
- `observability/prometheus/prometheus.yml` with `scrape_configs` per target.
- Service discovery: static configs using Docker Compose service names (e.g., `fastapi:8002`, `ingestion-worker:9091`).
- Exporters (`postgres_exporter`, `redis_exporter`, `statsd_exporter`) defined as Docker Compose services.

---

### E12-S2: Grafana System Overview Dashboard

**Story:** As a System Administrator, I want a Grafana dashboard showing overall system health so that I can see at a glance whether all services are operational.

**Acceptance Criteria:**
- Dashboard panels: service up/down status, CPU/memory usage (if node exporter is present), Postgres connection pool utilization, Redis memory usage, RabbitMQ queue depths.
- Auto-refreshes every 30 seconds.

**Technical Implementation Notes:**
- JSON dashboard definition in `observability/grafana/provisioning/dashboards/system_overview.json`.
- PromQL queries: `up{job="..."}`, `pg_stat_activity_count`, `redis_memory_used_bytes`, `rabbitmq_queue_messages`.

---

### E12-S3: Grafana API Performance Dashboard

**Story:** As a System Administrator, I want a Grafana dashboard showing FastAPI request metrics so that I can identify slow endpoints and error spikes.

**Acceptance Criteria:**
- Panels: request rate (RPS), p50/p95/p99 latency histograms, error rate (4xx/5xx), top 10 slowest endpoints.
- Filterable by time range and endpoint path.

**Technical Implementation Notes:**
- JSON dashboard in `observability/grafana/provisioning/dashboards/api_performance.json`.
- PromQL: `rate(http_requests_total[5m])`, `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`.
- Labels from `prometheus-fastapi-instrumentator`: `method`, `handler`, `status`.

---

### E12-S4: Grafana Ingestion Pipeline Dashboard

**Story:** As a System Administrator, I want a Grafana dashboard showing ingestion pipeline throughput and health so that I can detect backlogs or failures.

**Acceptance Criteria:**
- Panels: articles ingested over time, clusters processed/failed, average cluster processing duration, current queue depth, worker active tasks.
- Alert panel highlighting any queue depth exceeding threshold.

**Technical Implementation Notes:**
- JSON dashboard in `observability/grafana/provisioning/dashboards/ingestion_pipeline.json`.
- PromQL: `rate(prism_articles_ingested_total[5m])`, `prism_clusters_processed_total`, `prism_cluster_processing_duration_seconds`, `rabbitmq_queue_messages{queue="cluster_processing"}`.

---

### E12-S5: Grafana LLM Cost Tracking Dashboard

**Story:** As a System Administrator, I want a Grafana dashboard showing LLM token usage and estimated cost so that I can monitor and optimize AI spend.

**Acceptance Criteria:**
- Panels: total tokens in/out over time (by model, provider, agent), estimated cost (USD) over time, cost breakdown pie chart by agent, average latency by model.
- Filterable by provider (Ollama vs cloud) and agent name.

**Technical Implementation Notes:**
- JSON dashboard in `observability/grafana/provisioning/dashboards/llm_cost.json`.
- PromQL: `sum(rate(prism_llm_prompt_tokens_total[1h])) by (model, provider, agent)`, similar for completion tokens.
- Cost panel: uses a Grafana transformation to multiply token rates by per-model cost constants (or a recording rule in Prometheus).

---

### E12-S6: Prometheus Alerting Rules

**Story:** As a Platform Engineer, I want Prometheus alerting rules for critical thresholds so that on-call engineers are notified before users are impacted.

**Acceptance Criteria:**
- Alert rules defined for: API error rate > 5% for 5 min, queue depth > 1000 for 10 min, DB connection pool > 80% for 5 min, any service down for 2 min, ingestion worker not consuming for 10 min, LLM cost exceeding daily budget.
- Alerts route to a configurable notification channel (email, Slack webhook placeholder).

**Technical Implementation Notes:**
- `observability/prometheus/alerts/critical.yml` defines alerting rules in PromQL.
- Prometheus `alertmanager` (or Grafana alerting) routes alerts to configured receivers.
- Grafana contact points configured in provisioning YAML for email/webhook.

---

### E12-S7: LangSmith / Langfuse Agent Tracing

**Story:** As a Platform Engineer, I want every LangGraph pipeline run to produce a full execution trace in LangSmith or Langfuse so that I can visually debug the Map → Reduce → Debate flow and catch prompt drift or bias leakage.

**Acceptance Criteria:**
- Every ingestion pipeline run (per cluster) creates a trace with a unique `run_id`.
- The trace shows each node (Map per article, Reduce, Proponent, Skeptic, Judge) with: input, output, latency, token usage.
- Traces are searchable by `cluster_id`, `run_id`, or time range in the LangSmith/Langfuse UI.
- The `run_id` and `trace_url` are stored on the `event_clusters` row for admin linking.

**Technical Implementation Notes:**
- LangSmith: setting `LANGCHAIN_TRACING_V2=true` auto-traces all LangChain/LangGraph calls. `run_id` passed via `RunnableConfig({"run_id": cluster_id})`.
- Langfuse: `CallbackHandler(trace_id=cluster_id)` attached to the graph invocation in `ai/llm/callbacks.py`.
- After pipeline completion, the worker writes `trace_url` to `event_clusters.trace_url` column (constructed from the trace ID and host).
- Admin endpoint `GET /api/v1/admin/llm/traces/{cluster_id}` returns the URL.

---

### E12-S8: Sentry Distributed Tracing (Backend)

**Story:** As a Platform Engineer, I want Sentry to trace requests from the FastAPI endpoint through RabbitMQ to the LangGraph worker so that end-to-end latency and errors are correlated.

**Acceptance Criteria:**
- A Sentry transaction starts when a FastAPI request is received.
- When a RabbitMQ message is published, the Sentry trace context (trace ID, span ID) is included in the message headers.
- The worker extracts the trace context and continues the Sentry transaction.
- The full trace (API → queue → worker) is visible in Sentry's Performance tab.

**Technical Implementation Notes:**
- FastAPI: `sentry_sdk` with `FastApiIntegration` automatically creates transactions.
- RabbitMQ publish: inject `sentry-trace` and `baggage` headers into the message properties.
- Worker: extract headers and call `sentry_sdk.continue_trace(headers)` before processing.
- `sentry_sdk` integrations: `AioHttpIntegration` or custom for `aio-pika`.

---

### E12-S9: Sentry Frontend Release Tracking

**Story:** As a Platform Engineer, I want Sentry to associate frontend errors with specific releases and source maps so that stack traces are readable and regressions are tracked per deployment.

**Acceptance Criteria:**
- Each frontend build generates a unique release identifier (e.g., git SHA).
- Source maps are uploaded to Sentry during the CI build step.
- Errors in Sentry show deobfuscated stack traces with original file names and line numbers.
- The Sentry Releases page shows error counts per release.

**Technical Implementation Notes:**
- `@sentry/cli` or `@sentry/webpack-plugin` (or Vite equivalent) configured in the frontend build pipeline.
- Release: `REACT_APP_SENTRY_RELEASE` set to `git rev-parse --short HEAD` in CI.
- Source maps uploaded via `sentry-cli releases files $RELEASE upload-sourcemaps ./build/static/js`.

---

### E12-S10: Lightweight LLM-as-a-Judge Evaluation

**Story:** As a Platform Engineer, I want a standalone evaluation script that uses an LLM (via Ollama) to score the quality and bias of the Debate pipeline's output so that I can empirically demonstrate that the multi-agent system reduces bias.

**Acceptance Criteria:**
- A Python script `evaluation/run_bias_eval.py` accepts a sample of pipeline outputs (or fetches recent clusters from PostgreSQL).
- For each sample, the script prompts a local Ollama model to evaluate: balance (are multiple perspectives represented?), source diversity (are facts drawn from varied sources?), and absence of single-source bias.
- Each dimension is scored 1-5 with a short justification.
- The script outputs a summary report (text or JSON) with average scores across samples.
- The script is runnable locally with `python evaluation/run_bias_eval.py --sample-size 20` and requires only Ollama (no cloud API key).

**Technical Implementation Notes:**
- `evaluation/run_bias_eval.py` uses `langchain_ollama.ChatOllama` with `settings.ollama_host` (or a CLI arg `--ollama-url`).
- Evaluation prompt in `evaluation/prompts/bias_judge.py` instructs the LLM to output structured JSON: `{balance: {score, reason}, source_diversity: {score, reason}, bias_absence: {score, reason}}`.
- Samples fetched from PostgreSQL: queries `event_clusters` with `status=completed`, ordered by `created_at DESC`, limit N. Includes `debiased_summary`, `ner_tags`, and `source_urls`.
- Output: JSON report written to `evaluation/reports/{timestamp}.json` and a summary printed to stdout.
- Can be integrated into CI as a regression gate (fail if average score drops below threshold).

---
