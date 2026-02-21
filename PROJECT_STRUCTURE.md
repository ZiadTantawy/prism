# Prism — Project Structure

> Target folder layout for the Prism AI News Intelligence Platform.
> This document describes the intended structure. Directories and files listed here are not yet created; use this as the blueprint when scaffolding.

---

```
prism/
│
├── .env                              # Active environment variables (git-ignored)
├── .env.example                      # Documented template with safe defaults for every variable
├── .gitignore
├── docker-compose.yml                # All infrastructure + optional profiles (llm-local)
├── requirements.txt                  # Python dependencies (backend, workers, AI)
├── pyproject.toml                    # Optional: single source of truth for deps & project metadata
├── README.md                         # Project overview, quickstart, architecture summary
├── USER_STORIES.md                   # Exhaustive user stories (all 12 epics)
├── PROJECT_STRUCTURE.md              # This file
│
├── dags/                             # Airflow DAGs (mounted into Airflow containers)
│   ├── ingest_rss_metadata.py        # Tier 1: scrape RSS feeds, extract headlines, bulk-insert articles
│   ├── cluster_headlines.py          # Tier 1: embed headlines, HDBSCAN clustering, enqueue to RabbitMQ
│   └── utils/                        # Shared helpers for DAGs (feed parsing, DB helpers)
│       └── ...
│
├── src/                              # Backend Python package
│   │
│   ├── core/                         # Application-wide configuration and bootstrap
│   │   ├── __init__.py
│   │   ├── config.py                 # Pydantic Settings: all env vars, computed URLs, LLM provider config
│   │   ├── lifespan.py               # FastAPI lifespan: init/teardown of DB, Redis, Qdrant, Sentry, Prometheus
│   │   └── security.py               # JWT encoding/decoding, password hashing utilities
│   │
│   ├── api/                          # FastAPI application and route modules
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI app factory, middleware (CORS, rate limit), router mounting
│   │   ├── deps.py                   # Reusable dependencies: get_current_user, RoleChecker, rate limiter
│   │   └── v1/                       # Versioned API routes
│   │       ├── __init__.py
│   │       ├── auth.py               # Registration, login, token refresh, API key management
│   │       ├── feed.py               # Daily feed, entity context (Qdrant semantic search)
│   │       ├── chat.py               # "Ask Prism" chat (REST and/or WebSocket)
│   │       ├── watchlists.py         # Watchlist CRUD, alert listing
│   │       ├── firehose_ws.py        # B2B WebSocket: real-time cluster + sentiment streaming
│   │       ├── rag_workspace.py      # B2B: document upload, document list, private RAG chat
│   │       └── admin.py              # Admin: health, stats, Airflow proxy, queue depths, LLM usage
│   │
│   ├── shared/                       # Cross-cutting infrastructure clients (used by API + workers)
│   │   ├── __init__.py
│   │   ├── metrics.py                # Prometheus custom counters, histograms, gauges (shared definitions)
│   │   │
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── clients/
│   │   │   │   └── postgres.py       # Async engine, session factory, get_session(), ping(), close()
│   │   │   └── postgres/
│   │   │       ├── __init__.py
│   │   │       ├── base.py           # DeclarativeBase, IdMixin, TimestampMixin
│   │   │       └── models/
│   │   │           ├── __init__.py
│   │   │           ├── user.py
│   │   │           ├── subscription.py
│   │   │           ├── article.py
│   │   │           ├── source.py
│   │   │           ├── event_cluster.py
│   │   │           ├── watchlist.py
│   │   │           ├── api_key.py
│   │   │           ├── alert.py
│   │   │           ├── document.py
│   │   │           └── llm_usage_log.py
│   │   │
│   │   ├── redis/
│   │   │   ├── __init__.py
│   │   │   └── client.py             # Async Redis client, connection pool, cache utilities
│   │   │
│   │   ├── qdrant/
│   │   │   ├── __init__.py
│   │   │   └── client.py             # AsyncQdrantClient wrapper, ensure_collection(), search helpers
│   │   │
│   │   ├── minio/
│   │   │   ├── __init__.py
│   │   │   └── client.py             # Async MinIO client, ensure_bucket(), upload/download helpers
│   │   │
│   │   └── rabbitmq/
│   │       ├── __init__.py
│   │       └── client.py             # aio-pika connection, publish helper, channel pool
│   │
│   ├── services/                     # Business logic layer (used by API routes and workers)
│   │   ├── __init__.py
│   │   ├── feed_service.py           # Feed query, cache, entity context retrieval
│   │   ├── auth_service.py           # Registration, login, token issuance logic
│   │   ├── subscription_service.py   # Tier management, quota checks
│   │   ├── alert_service.py          # Alert matching, delivery
│   │   ├── firehose_service.py       # WebSocket connection management, broadcast
│   │   └── rag_service.py            # Document upload orchestration, private chat routing
│   │
│   └── db/                           # Database migrations
│       ├── alembic.ini               # Alembic config (points to Settings.async_database_url)
│       └── alembic/
│           ├── env.py                # Async migration runner, imports Base + all models
│           ├── script.py.mako        # Migration template
│           └── versions/             # Auto-generated migration scripts
│               └── ...
│
├── workers/                          # Standalone RabbitMQ consumer processes
│   │
│   ├── ingestion_worker/             # Tier 2: MapReduce + Debate pipeline runner
│   │   ├── __init__.py
│   │   ├── consumer.py               # aio-pika consumer loop, message handling, error/retry logic
│   │   ├── pipeline.py               # Orchestrates: build graph -> invoke -> store results
│   │   └── metrics.py                # Worker-specific Prometheus metrics, /metrics HTTP server
│   │
│   ├── alert_worker/                 # Watchlist matching + alert delivery
│   │   ├── __init__.py
│   │   └── consumer.py
│   │
│   └── rag_ingest_worker/            # Private RAG: download from MinIO -> OCR/parse -> chunk -> embed -> Qdrant
│       ├── __init__.py
│       └── consumer.py
│
├── ai/                               # LangChain / LangGraph AI layer
│   │
│   ├── __init__.py
│   │
│   ├── llm/                          # Provider abstraction and instrumentation
│   │   ├── __init__.py
│   │   ├── factory.py                # get_llm(role) -> ChatOllama | ChatOpenAI | ChatAnthropic (from config)
│   │   ├── embeddings.py             # get_embeddings() -> OllamaEmbeddings | OpenAIEmbeddings (from config)
│   │   └── callbacks.py              # TokenTrackingHandler (Prometheus + Postgres), LangSmith/Langfuse setup
│   │
│   ├── graphs/                       # LangGraph state graphs
│   │   ├── __init__.py
│   │   ├── map_reduce.py             # Map (parallel fact extraction) + Reduce (dedup, conflict flagging)
│   │   ├── debate.py                 # Proponent -> Skeptic -> Judge subgraph
│   │   └── rag_chat.py               # RAG agent for "Ask Prism" and B2B private chat
│   │
│   └── prompts/                      # Prompt templates (one file per agent/task)
│       ├── __init__.py
│       ├── map_extract.py            # Structured extraction prompt for Map nodes
│       ├── proponent.py              # Mainstream narrative construction
│       ├── skeptic.py                # Counter-narrative, attack unsupported claims
│       ├── judge.py                  # Debiased synthesis, confidence scoring
│       └── rag_answer.py             # Grounded Q&A with source citation
│
├── evaluation/                       # Lightweight LLM-as-a-Judge bias evaluation
│   ├── run_bias_eval.py              # CLI script: sample clusters -> Ollama judge -> scored report
│   ├── prompts/
│   │   └── bias_judge.py             # Evaluation prompt: balance, source diversity, bias absence
│   ├── reports/                      # Output directory for JSON evaluation reports (git-ignored)
│   │   └── .gitkeep
│   └── README.md                     # Usage instructions for the evaluation script
│
├── frontend/                         # React + Redux Toolkit + Tailwind CSS + Helmet
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.js
│   ├── vite.config.ts                # Or CRA config; Vite recommended
│   ├── index.html
│   ├── public/
│   │   └── ...
│   └── src/
│       ├── app/
│       │   ├── App.tsx               # Root component, router, error boundary
│       │   ├── store.ts              # Redux configureStore
│       │   ├── routes.tsx            # Route definitions with lazy loading
│       │   └── sentry.ts            # Sentry Browser SDK initialization
│       │
│       ├── features/                 # Redux slices + related components (feature-based structure)
│       │   ├── auth/
│       │   │   ├── userAuthSlice.ts
│       │   │   ├── LoginPage.tsx
│       │   │   └── RegisterPage.tsx
│       │   ├── feed/
│       │   │   ├── feedSlice.ts
│       │   │   └── FeedPage.tsx
│       │   ├── sidebar/
│       │   │   ├── sidebarContextSlice.ts
│       │   │   └── SidebarContext.tsx
│       │   ├── chat/
│       │   │   ├── chatSlice.ts
│       │   │   └── ChatPage.tsx
│       │   └── watchlist/
│       │       ├── watchlistSlice.ts
│       │       └── WatchlistPage.tsx
│       │
│       ├── components/               # Shared UI components
│       │   ├── EventCard.tsx
│       │   ├── EntityPill.tsx
│       │   ├── ChatMessage.tsx
│       │   ├── Navbar.tsx
│       │   ├── Sidebar.tsx
│       │   ├── LoadingSpinner.tsx
│       │   └── ...
│       │
│       ├── pages/                    # Top-level page components (non-feature pages)
│       │   ├── WorkspacePage.tsx      # B2B private RAG workspace
│       │   ├── AdminPage.tsx         # Admin portal (health, stats, LLM usage, queues)
│       │   └── SettingsPage.tsx
│       │
│       └── lib/                      # Utility functions, API client, constants
│           ├── api.ts                # Axios/fetch wrapper, base URL, interceptors
│           └── constants.ts
│
├── observability/                    # Prometheus, Grafana, and alerting configuration
│   │
│   ├── prometheus/
│   │   ├── prometheus.yml            # Scrape configs for all targets
│   │   └── alerts/
│   │       └── critical.yml          # Alerting rules: error rate, queue backlog, service down, cost budget
│   │
│   └── grafana/
│       └── provisioning/
│           ├── datasources/
│           │   └── prometheus.yml    # Auto-provisioned Prometheus datasource
│           └── dashboards/
│               ├── dashboards.yml    # Dashboard provider config
│               ├── system_overview.json
│               ├── api_performance.json
│               ├── ingestion_pipeline.json
│               └── llm_cost.json
│
├── scripts/                          # Operational and one-off scripts
│   ├── seed_sources.py               # Seed initial RSS feed sources into the database
│   ├── pull_ollama_models.sh         # Download required Ollama models for local dev
│   └── ...
│
└── tests/
    ├── conftest.py                   # Shared fixtures: test DB, Redis mock, test client
    ├── unit/                         # Unit tests (services, utils, LLM factory, prompts)
    │   └── ...
    ├── integration/                  # Integration tests (API endpoints, DB, Redis, Qdrant)
    │   └── ...
    └── e2e/                          # End-to-end tests (full pipeline, frontend flows)
        └── ...
```

---

## Directory Rationale

### `dags/`
Mounted directly into Airflow containers via Docker Compose volume. Contains only Airflow DAG definitions and lightweight utilities. Tier 1 of the ingestion pipeline: RSS scraping, headline embedding, HDBSCAN clustering, and RabbitMQ enqueue. Kept separate from `src/` because Airflow has its own Python environment and execution model.

### `src/`
The main backend Python package, housing everything the FastAPI application needs:
- **`core/`** — Configuration (Pydantic Settings), FastAPI lifespan (startup/shutdown hooks), and security utilities (JWT, password hashing). The single source of truth for all environment-driven settings, including LLM provider config and Sentry DSN.
- **`api/`** — FastAPI app factory, middleware, and versioned routes. Each route module (`auth.py`, `feed.py`, `chat.py`, etc.) corresponds to a domain and maps to one or more epics. `deps.py` holds reusable dependencies (authentication, role checking, rate limiting).
- **`shared/`** — Infrastructure client wrappers for Postgres, Redis, Qdrant, MinIO, and RabbitMQ. Each client provides async initialization, health check (`ping`), and graceful shutdown. Also contains `metrics.py` for Prometheus metric definitions shared between the API and workers. The `database/postgres/models/` directory holds all SQLAlchemy models.
- **`services/`** — Business logic layer. Routes call services; services call shared clients. This separation keeps route handlers thin and makes logic reusable across the API and workers.
- **`db/`** — Alembic migration framework. `env.py` imports `Base` and all models for autogenerate support. Migration scripts live in `versions/`.

### `workers/`
Standalone, long-running Python processes that consume from RabbitMQ queues. Each worker is independently deployable and containerizable:
- **`ingestion_worker/`** — Tier 2 of the pipeline. Receives cluster messages, runs the full LangGraph MapReduce + Debate graph (from `ai/`), stores results in Postgres and Qdrant. Exposes its own `/metrics` endpoint for Prometheus.
- **`alert_worker/`** — Matches completed clusters against user watchlists and delivers alerts.
- **`rag_ingest_worker/`** — Processes enterprise document uploads: downloads from MinIO, parses/OCRs, chunks, embeds, and upserts to tenant-specific Qdrant collections.

### `ai/`
All LangChain and LangGraph code, fully decoupled from the web framework and workers:
- **`llm/`** — Provider abstraction layer. `factory.py` resolves `ChatOllama`, `ChatOpenAI`, or `ChatAnthropic` based on per-role environment variables (e.g., `LLM_MAP_PROVIDER=ollama`). `callbacks.py` contains the `TokenTrackingHandler` (writes to Prometheus counters and the `llm_usage_log` Postgres table) and LangSmith/Langfuse tracing setup.
- **`graphs/`** — LangGraph `StateGraph` definitions. `map_reduce.py` implements the Map (parallel per-article extraction via `Send()`) and Reduce (dedup + conflict flagging) phases. `debate.py` implements the Proponent → Skeptic → Judge subgraph. `rag_chat.py` implements the RAG agent used by "Ask Prism" and B2B private chat.
- **`prompts/`** — Prompt templates, one file per agent role. Isolated for easy iteration and version control.

### `evaluation/`
A standalone, lightweight evaluation harness for auditing the anti-bias moat. `run_bias_eval.py` is a CLI script that samples pipeline outputs, sends them to a local Ollama model acting as an LLM judge, and produces scored reports (balance, source diversity, bias absence). Requires only Ollama — no cloud API keys. Runnable locally or in CI.

### `frontend/`
React single-page application with Redux Toolkit for state management, Tailwind CSS for styling, and React Helmet for dynamic SEO meta tags:
- **`app/`** — Application shell: root component, Redux store, route config, Sentry initialization.
- **`features/`** — Feature-based structure: each feature (auth, feed, sidebar, chat, watchlist) has its own Redux slice and primary component.
- **`components/`** — Shared, presentational UI components (cards, pills, spinners, nav).
- **`pages/`** — Top-level pages that don't fit neatly into a feature (workspace, admin, settings).
- **`lib/`** — Utility layer: API client wrapper, constants.

### `observability/`
Configuration-only directory (no application code). Mounted into Prometheus and Grafana containers:
- **`prometheus/`** — `prometheus.yml` (scrape configs for all targets) and `alerts/` (PromQL alerting rules).
- **`grafana/`** — Provisioning YAML for auto-configured datasources and JSON dashboard definitions (system overview, API performance, ingestion pipeline, LLM cost).

### `scripts/`
Operational utilities: seed initial RSS sources into the DB, pull required Ollama models, data backfill scripts, etc. Not part of the runtime application.

### `tests/`
Three-tier test structure:
- **`unit/`** — Fast, isolated tests for services, utilities, LLM factory, and prompt formatting. No external dependencies.
- **`integration/`** — Tests that hit real (or containerized) databases, Redis, and Qdrant. Uses test fixtures from `conftest.py`.
- **`e2e/`** — End-to-end tests covering full pipeline runs and frontend flows.
