# Favicon Scanner (Hexagonal + Celery worker pool)

**What it does**
- API accepts IPs/ranges/hosts, scans `/favicon.ico`, MD5-hashes body, matches Rapid7 `favicons.xml`.
- Proper worker pool: **Celery + Redis**. API enqueues jobs; workers process async.
- Results stored in **RedisResultStore** (swappable later). Structured JSON logs.
- Safe under load: bounded concurrency, per-host limits, max-bytes, retries, sockets cap.

## Quickstart (local)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

mkdir -p data
curl -L -o data/favicons.xml https://raw.githubusercontent.com/rapid7/recog/main/xml/favicons.xml

export REDIS_URL=redis://localhost:6379/0
export FAVICONS_PATH=./data/favicons.xml
export VERIFY_TLS=false
export CONCURRENCY=200
export PER_HOST_LIMIT=5
export TIMEOUT_SECONDS=3.0
export MAX_BYTES=2097152
export RETRIES=1
export RETRY_BACKOFF_MS=250
export MAX_SOCKETS_PER_JOB=10000

# Terminal A
uvicorn app.adapters.api.fastapi_app:app --reload

# Terminal B
celery -A app.adapters.system.celery_app.celery_app worker --loglevel=INFO -c 4


# Exercise
resp=$(curl -s -X POST http://127.0.0.1:8000/scan \
  -H "Content-Type: application/json" \
  -d '{"targets":["93.184.216.34","example.com"],"ports":[80,443]}')

SCAN_ID=$(echo "$resp" | jq -r .scan_id)
until [[ "$(curl -s http://127.0.0.1:8000/scan/$SCAN_ID | jq -r .status)" != "pending" ]]; do
  printf '.'; sleep 1; done; echo
curl -s http://127.0.0.1:8000/scan/$SCAN_ID | jq

# Docker Compose

curl -L -o data/favicons.xml https://raw.githubusercontent.com/rapid7/recog/main/xml/favicons.xml
cd docker
docker compose build
docker compose up -d
curl -s http://127.0.0.1:8000/health
docker compose up -d --scale worker=3
