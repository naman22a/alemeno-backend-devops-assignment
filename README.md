# AI-Powered Transaction Processing Pipeline

A FastAPI backend that accepts a dirty transactions CSV, processes it asynchronously
through Celery + Redis, uses a local Ollama LLM for classification and narrative
generation, and exposes a polling API for results.

---

## Quick Start

```bash
# 1. Clone the repo
git clone git@github.com:naman22a/alemeno-backend-devops-assignment.git
cd alemeno-backend-devops-assignment

# 2. Copy the env file (defaults work out of the box)
cp .env.example .env

# 3. Start everything - api, worker, redis, postgres, and ollama
docker compose up
```

The first boot takes a few minutes because the `ollama-init` service pulls
`llama3.2:3b` (~2GB) into the `ollama_data` volume. Subsequent boots are instant.

Once you see `Application startup complete` in the api logs, the service is ready.

---

## API Endpoints

### Upload a CSV

```bash
curl -X POST http://localhost:8000/jobs/upload \
  -F "file=@sample_data/transactions.csv"
```

Response:

```json
{ "job_id": "3f2a...", "status": "pending" }
```

---

### Poll Job Status

```bash
curl http://localhost:8000/jobs/<job_id>/status
```

Response while processing:

```json
{"job_id": "...", "status": "processing", "filename": "transactions.csv", ...}
```

Response when done:

```json
{
  "job_id": "...",
  "status": "completed",
  "row_count_raw": 90,
  "row_count_clean": 88,
  "summary": {
    "total_spend_inr": 284500.0,
    "total_spend_usd": 237.5,
    "top_merchants": [...],
    "anomaly_count": 4,
    "narrative": "Spending is dominated by...",
    "risk_level": "medium"
  }
}
```

---

### Get Full Results

```bash
curl http://localhost:8000/jobs/<job_id>/results
```

Returns cleaned transactions, flagged anomalies, per-category spend breakdown,
and the LLM narrative summary.

---

### List All Jobs

```bash
# All jobs
curl http://localhost:8000/jobs

# Filter by status
curl "http://localhost:8000/jobs?status=completed"
curl "http://localhost:8000/jobs?status=failed"
```

---

## Architecture

```
Client
  │
  ▼ POST /jobs/upload
FastAPI (api service)
  │  • validates CSV
  │  • writes Job(status=pending) → PostgreSQL
  │  • saves file to /app/uploads/
  │  • enqueues process_job task → Redis
  │
  ▼ (asynchronously)
Celery Worker
  │
  ├─ a) clean_transactions()      — normalise dates, strip $, uppercase, dedup
  ├─ b) detect_anomalies()        — 3x-median outlier, USD on domestic brand
  ├─ c) classify_uncategorized()  — batched LLM call via Ollama
  ├─ d) generate_narrative()      — single LLM call for narrative + risk_level
  └─ bulk_insert_transactions()   → PostgreSQL
     upsert_job_summary()         → PostgreSQL
     mark_job_completed()         → PostgreSQL

Client
  ▼ GET /jobs/{id}/status  (polls until completed)
  ▼ GET /jobs/{id}/results (fetches the structured report)
```

### Why each technology was chosen

| Technology         | Reason                                                                                                                                                                                                  |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **FastAPI**        | Native async, Pydantic schema validation, auto OpenAPI docs                                                                                                                                             |
| **Celery + Redis** | Mature, battle-tested, retry primitives built in. Fits this workload better than RQ because Celery's `task_track_started=True` lets the API return a `processing` status without polling Redis directly |
| **PostgreSQL**     | JSONB for `top_merchants`, transactional integrity for job state transitions                                                                                                                            |
| **SQLAlchemy**     | Repository pattern: swap Postgres for SQLite in tests trivially                                                                                                                                         |
| **Ollama (local)** | No API key, no spend. Runs on RTX 5070. Model is swappable via `OLLAMA_MODEL` env var                                                                                                                   |
| **tenacity**       | Exponential backoff in one decorator. Assignment 5(e) in ~5 lines                                                                                                                                       |
| **pandas**         | Vectorised cleaning/anomaly math. Median-per-account-group is one `groupby`                                                                                                                             |

---

## Bottlenecks at 100× Traffic

**Where it breaks first:**

1. **PostgreSQL connection pool** — `pool_size=10, max_overflow=20` means ~30
   concurrent DB connections. At 100× load you'd saturate this before anything else.
   Fix: PgBouncer in transaction-mode pooling in front of Postgres.

2. **Single Celery worker / single queue** — one worker processes jobs serially.
   Fix: scale `worker` replicas in docker-compose (or Kubernetes deployments).
   The worker is already stateless so horizontal scaling is trivial.

3. **CSV files on the API container's local disk** — the worker needs to read the
   same file, which works when api and worker share a volume mount, but breaks as
   soon as you run multiple API replicas on different hosts.
   Fix: upload to S3/GCS on receipt; pass the object key (not a file path) in the
   task payload.

4. **Ollama as a single container** — LLM inference is the slowest step by far.
   Fix: expose Ollama as a separate service behind a load balancer; run multiple
   replicas on GPU nodes; or switch to a managed API (Gemini / Bedrock) with a
   higher rate limit.

**Next-iteration architectural changes for enterprise scale:**

| Change                                     | Trade-off                                                           |
| ------------------------------------------ | ------------------------------------------------------------------- |
| Alembic migrations instead of `create_all` | more setup, but schema changes are auditable and reversible         |
| S3 for CSV storage                         | adds a dependency, eliminates shared-volume requirement             |
| PgBouncer connection pooling               | extra hop, but prevents connection exhaustion under load            |
| Celery beat + priorities                   | separate fast-poll queue from slow LLM queue                        |
| OpenTelemetry tracing                      | adds instrumentation overhead, gives you per-step latency breakdown |
| Read replica for GET /results              | adds replication lag, removes read load from primary                |
