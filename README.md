#  Favicon Scanner

A lightweight **FastAPI + Celery** service that fingerprints web applications
by fetching `/favicon.ico`, hashing it, and matching it against the
[Rapid7 Recog](https://github.com/rapid7/recog) database.

This is the backend challenge implementation (Forescout-style exercise),
structured using **Ports & Adapters (Hexagonal Architecture)** for testability
and easy extension (e.g., switch storage, queue, or fetcher adapters).

---

##  Architecture

```
.
├─ app/
│  ├─ domain/              # business logic (ScanService)
│  ├─ ports/               # abstract interfaces (repositories, fetcher, result store)
│  └─ adapters/            # infrastructure
│     ├─ api/              # FastAPI REST API
│     ├─ http/             # async HTTP fetcher
│     ├─ repositories/     # Recog XML parser
│     └─ system/           # Redis, Celery, logging
├─ docker/                 # docker & compose setup
├─ data/                   # favicons.xml cache
├─ tests/                  # unit + integration tests
│ 
└─ pyproject.toml
```

### Components
| Layer | Responsibility |
|-------|----------------|
| **Domain** | Pure business logic (`ScanService`) orchestrates scanning |
| **Ports** | Abstract boundaries for repositories and external systems |
| **Adapters** | Concrete implementations (HTTP fetcher, Redis store, Celery worker, API) |
| **Infrastructure** | Docker, Redis, RabbitMQ(Only for testing scan), Celery integration |

---

##  Quick Start (Local with Docker)

### Prerequisites
- Docker + Docker Compose v2
- Python ≥ 3.11 (optional if you only run in Docker)

### Build & Start All Services
```bash
docker compose -f docker/docker-compose.yml up -d --build
```

This launches:
| Service | Description | Port |
|----------|--------------|------|
| `api` | FastAPI server (Uvicorn) | [http://localhost:8000/docs](http://localhost:8000/docs) |
| `worker` | Celery worker processing scan jobs | — |
| `redis` | Queue + result backend | 6379 |
| `rabbitmq` | Dummy scan target (management UI) | [http://localhost:15673](http://localhost:15673) |

Once up:
```bash
docker compose -f docker/docker-compose.yml ps
```
All services should show **Up (healthy)**.

---

## API Endpoints

| Method | Path | Description |
|---------|------|--------------|
| `POST` | `/scan` | Submit a scan request; returns `scan_id` |
| `GET` | `/scan/{scan_id}` | Fetch scan result |
| `GET` | `/docs` | Swagger UI |


##  Configuration (`app/config.py`)

Runtime configuration is managed via `app/config.py`, using a Pydantic `Settings` model.  
This allows **strict typing**, **dotenv or environment overrides**, and **safe defaults** when deploying locally or in CI.

| Variable | Default | Description |
|-----------|----------|-------------|
| **API_KEY** | `None` | Optional API key (reserved for future authentication) |
| **VERIFY_TLS** | `false` | Whether to verify HTTPS certificates when fetching favicons |
| **CONCURRENCY** | `200` | Max concurrent async requests per scan job |
| **PER_HOST_LIMIT** | `5` | Max concurrent connections per host |
| **TIMEOUT_SECONDS** | `3.0` | Timeout for each favicon request |
| **MAX_TARGETS** | `2048` | Maximum total targets per scan job |
| **MAX_SOCKETS_PER_JOB** | `10000` | Upper bound on aiohttp connector sockets |
| **MAX_BYTES** | `2097152` (2 MB) | Maximum response size per favicon fetch |
| **RETRIES** | `1` | Number of retries for failed fetches |
| **RETRY_BACKOFF_MS** | `250` | Delay between retries (milliseconds) |
| **FAVICONS_PATH** | `./data/favicons.xml` | Local path to Recog fingerprint XML file |
| **DEFAULT_PORTS** | `[80, 443, 8080]` | Default ports used when user omits ports in scan request |
| **REDIS_URL** | `redis://localhost:6379/0` | Redis connection string for Celery and result storage |
| **CELERY_WORKER_CONCURRENCY** | `4` | Number of concurrent Celery worker processes |

### Example
```bash
curl -X POST http://127.0.0.1:8000/scan   -H "Content-Type: application/json"   -d '{"targets":["rabbitmq"], "ports":[15672]}'
```

Response:
```json
{
  "scan_id": "501206ed-3e25-4cc4-abd1-2d3bf39ff3ee",
  "status": "pending",
  "job_id": "5ee9c282-19ae-4b94-9dc4-de6a5daf0280"
}
```

Then poll:
```bash
curl http://127.0.0.1:8000/scan/501206ed-3e25-4cc4-abd1-2d3bf39ff3ee
```

Expected `"RabbitMQ"` match in results.

---

##  Running Tests

### Run everything inside Docker (recommended)
```bash
docker compose -f docker/docker-compose.yml run --rm tests
```

### Run specific test file
```bash
docker compose -f docker/docker-compose.yml run --rm tests pytest -v tests/test_scan_rabbitmq.py
```

### Run locally (without Docker)
If services are already up on your host:
```bash
pytest -v
```

---

##  Logs & Debugging

### View service logs
```bash
docker compose -f docker/docker-compose.yml logs --tail=100 api
docker compose -f docker/docker-compose.yml logs -f worker
```

### Follow all logs live
```bash
docker compose -f docker/docker-compose.yml logs -f
```

### Pretty-print structured logs (JSON → text)
```bash
docker compose -f docker/docker-compose.yml logs -f api | jq -r '"\(.level) \(.msg) \(.extra // {})"'
```

---

## Development Notes

### Background Tasks
- The API enqueues scan jobs via Celery to Redis.
- Each worker performs async HTTP fetches (100+ concurrent) per job.
- Results are stored back into Redis via the `ResultStorePort`.

### Dummy RabbitMQ Target
RabbitMQ’s management UI (`:15672` internal / `:15673` host) is used
as a known favicon source to verify Recog detection.

### Environment Variables
| Variable | Default | Description |
|-----------|----------|-------------|
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` | Celery broker |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/1` | Celery result backend |
| `FAVICONS_PATH` | `/data/favicons.xml` | Recog DB path |
| `MAX_TARGETS` | `100` | Maximum concurrent targets |

---

##  Development Workflow

### Rebuild / refresh code
```bash
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml up -d
```

### Run tests with live source mount
The `tests` service bind-mounts `../` → `/app`, so code edits are visible immediately.

### Inspect running containers
```bash
docker exec -it docker-api-1 sh
docker exec -it docker-worker-1 sh
```

---

##  Tech Stack

| Area | Tool |
|------|------|
| API Framework | FastAPI |
| Concurrency | asyncio + aiohttp |
| Queue | Celery + Redis |
| Result Store | Redis Hashes |
| Fingerprint DB | Rapid7 Recog (XML) |
| Testing | pytest + requests |
| Containerization | Docker Compose |
| Logging | JSON structured logs via `logging_cfg.py` |

---

##  Example Workflow (end-to-end)

```bash
# 1. Start all services
docker compose -f docker/docker-compose.yml up -d --build

# 2. Trigger scan against dummy RabbitMQ
curl -X POST http://127.0.0.1:8000/scan   -H "Content-Type: application/json"   -d '{"targets":["rabbitmq"],"ports":[15672]}'

# 3. Poll result until done
curl http://127.0.0.1:8000/scan/<SCAN_ID>

# 4. Run integration test
docker compose -f docker/docker-compose.yml run --rm tests pytest -v tests/test_scan_rabbitmq.py
```


