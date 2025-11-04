# docker/Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/app \
    DATA_DIR=/data \
    FAVICONS_PATH=/data/favicons.xml \
    FAVICONS_URL=https://raw.githubusercontent.com/rapid7/recog/master/xml/favicons.xml

RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates bash \
    && rm -rf /var/lib/apt/lists/*

WORKDIR ${APP_HOME}

# Deps first (better layer cache)
COPY requirements.txt requirements.txt
RUN python -m pip install --upgrade pip \
 && pip install -r requirements.txt

# App code
COPY app app
COPY tests tests
COPY pyproject.toml pyproject.toml
RUN pip install -e .

# Data + entrypoint
RUN mkdir -p ${DATA_DIR}
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
# Default command (api). The worker service overrides this in compose.
CMD ["uvicorn", "app.adapters.api.fastapi_app:app", "--host", "0.0.0.0", "--port", "8000"]
