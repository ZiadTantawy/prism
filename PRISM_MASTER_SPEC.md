# Prism: Master Technical Specification (v3.0 - Super Optimized)

## 1. Product Vision & Strategy

Prism is an end-to-end AI full-stack news intelligence platform. The core differentiator (moat) is delivering anti-bias, bite-sized news with deep, automated historical and financial context.

**Primary Goal:** Serve as a highly scalable production platform for consumers and enterprises, while functioning as a masterclass in advanced, data-intensive system design.

**Target Audience:**
- **B2C:** Busy consumers and retail investors (focus regions: Egypt, US, Global) who need quick macro-perspectives and financial context.
- **B2B:** Trading firms, PR agencies, and local MENA/Egyptian enterprises requiring structured intelligence and private RAG workspaces.

---

## 2. Technology Stack (Strict Constraints)

The system is built on a modern, decoupled architecture heavily utilizing asynchronous operations to handle high-throughput data ingestion and AI inference.

| Layer | Technology |
|-------|------------|
| **Frontend Application** | React, Tailwind CSS, Helmet (for dynamic SEO meta tags), and Redux Toolkit (RTK) for complex global state management. |
| **Backend API** | FastAPI (Async Python) for high-concurrency REST/WebSocket routing. |
| **AI Orchestration** | LangChain (for LLM abstraction, prompt templates, tool definitions) and LangGraph (for stateful, multi-agent workflow routing and parallel execution). |
| **Relational Database** | PostgreSQL (accessed via asyncpg/SQLAlchemy) for structured user, subscription, and metadata storage. |
| **Vector Database** | Qdrant for storing and retrieving high-dimensional embeddings (AI/RAG semantic search). |
| **Data Orchestration** | Apache Airflow for scheduling and managing complex scraping/ingestion Directed Acyclic Graphs (DAGs). |
| **Message Broker** | RabbitMQ for decoupled, asynchronous task queuing. |
| **Caching & State** | Redis (async) for rate-limiting, session management, and caching high-volume read endpoints. |
| **Object Storage** | MinIO (S3-compatible) for unstructured data (images, generated PDFs, raw SEC/Edgar financial filings). |

---

## 3. System Architecture & Components

The architecture is divided into three primary operational domains:

### A. The Agentic Ingestion Pipeline (Airflow → RabbitMQ → LangGraph)

To process wide volumes of news without exorbitant LLM costs, the ingestion pipeline utilizes a **Two-Tiered Agentic MapReduce architecture** powered by LangGraph:

**Tier 1: Shallow Sync & Clustering (Airflow)**

- Airflow DAGs scrape lightweight metadata (Headline, Source, URL, Timestamp) from RSS feeds and APIs.
- Headlines are vectorized and clustered using HDBSCAN to group identical news events.

**Tier 2: LangGraph MapReduce & Multi-Agent Debate (Python Workers)**

- The Python worker receives an event cluster (e.g., 45 articles) from RabbitMQ and instantiates a LangGraph StateGraph.
- **The "Map" Phase (Parallel Execution):** Utilizing LangGraph's `Send()` API, the graph dynamically spawns parallel nodes for each of the 45 articles. Each node uses LangChain and a fast, small-context LLM strictly to extract atomic facts and Named Entities (NER) into structured JSON.
- **The "Reduce" Phase (State Merging):** LangGraph's built-in state reducers (using Python's TypedDict and Annotated types) mathematically aggregate the 45 JSON outputs, deduplicating identical facts and explicitly flagging conflicting data points (discrepancies between sources).
- **The Debate Phase (Anti-Bias Synthesis):** The compiled state is passed to a Multi-Agent Debate subgraph:
  - **The Proponent Agent:** Constructs a narrative highlighting mainstream implications.
  - **The Skeptic Agent:** Attacks the narrative using fringe facts and source discrepancies.
  - **The Judge Agent:** Observes the graph state history and writes the final, debiased Prism summary.
- **Storage:** The worker saves the final debiased text, NER tags, and all 45 source URLs to PostgreSQL. The semantic vector embedding of the final summary is saved to Qdrant.

### B. The Core API Backend (FastAPI + Redis + PostgreSQL/Qdrant)

- Handles all client routing asynchronously.
- Reads the aggregated user feed heavily from Redis to ensure low-latency delivery.
- When a user queries historical context, FastAPI queries Qdrant for semantic neighbors and returns the synthesized data.

### C. The Client Application (React + Redux Toolkit)

- **Redux Architecture:** Utilizes feature-based slices (e.g., `feedSlice`, `sidebarContextSlice`, `userAuthSlice`) to manage global state without prop-drilling.
- **UI/UX:** Renders the feed and manages the dynamic sidebar state. When a user clicks an inline highlighted entity, Redux dispatches an action to fetch Qdrant historical context and updates the `sidebarContextSlice`, causing the sidebar to slide out natively.
- **Chat Integration:** The "Ask Prism" chat interface maintains its message history in Redux, sending user queries to the FastAPI backend, which invokes a LangGraph retrieval-agent to query MinIO/Qdrant.

---

## 4. Core Application Flows

### Flow 1: B2C - The "Discover" Loop & Push-then-Pull Context

- **Trigger:** User loads the frontend application.
- **Action:** React dispatches a Redux thunk to fetch the daily feed from the FastAPI/Redis backend.
- **Interaction:** The user reads a summary. Clicking a highlighted entity dispatches an action to load historical context into the Redux store, popping open the sidebar. Alternatively, the user clicks "Ask Prism" to open a chat window for deep-dive financial Q&A (powered by a LangGraph RAG agent).

### Flow 2: B2C - Watchlists & Market Alerts

- **Trigger:** User subscribes to specific tickers (e.g., AAPL) or macro topics.
- **Action:** Preferences are saved in PostgreSQL.
- **Resolution:** When the Airflow pipeline finalizes an event cluster matching those tags, it checks user thresholds and triggers an asynchronous RabbitMQ worker to push an alert to the user.

### Flow 3: B2B - The Firehose API

- **Trigger:** Algorithmic trading firm authenticates via API key.
- **Action:** Client opens a WebSocket connection to FastAPI.
- **Resolution:** As the LangGraph Reduce phase finalizes fact extraction and calculates sentiment ratios (e.g., 40 positive articles vs. 5 negative), FastAPI streams the structured JSON directly to the enterprise client.

### Flow 4: B2B - Secure Private RAG Workspace

- **Trigger:** Enterprise user uploads internal financial documents (PDFs).
- **Action:** FastAPI streams the raw file to MinIO. A RabbitMQ worker uses LangChain document loaders to OCR/parse the document, chunks it, embeds it, and saves it to a private, isolated collection in Qdrant.
- **Resolution:** The enterprise user interacts with a private LangGraph chat interface that cross-references global news with their proprietary documents.

### Flow 5: System Admin - Pipeline & AI Observability

- **Trigger:** Admin accesses the internal portal.
- **Action:** FastAPI serves an aggregated dashboard pulling health metrics from Airflow, queue depths from RabbitMQ, and LangGraph execution traces.
- **Resolution:** Admin can monitor the token cost/latency of the MapReduce phases, manually re-trigger failed DAGs, or adjust the HDBSCAN clustering parameters.

---

## 5. Instructions for LLM Prompting

When passing this document to an LLM to generate User Stories, use the following prompt:

> **You are an Agile Product Owner. Review the provided 'Prism: Master Technical Specification (v3.0)'. Based on this architecture and the listed application flows, generate detailed, development-ready User Stories.**
>
> **For each story, follow this exact format:**
>
> - **Story:** (As a [Stakeholder], I want to [Action] so that [Value])
> - **Acceptance Criteria:** (Bullet points of testable conditions)
> - **Technical Implementation Notes:** (Specifically detail which technologies from the strict tech stack—FastAPI, React, Redux Toolkit, Postgres, Qdrant, Airflow, RabbitMQ, Redis, MinIO, LangGraph, LangChain—will be utilized to satisfy the criteria, and how they interact.)
