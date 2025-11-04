# /docker/Dockerfile
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FAVICONS_PATH=/app/data/favicons.xml

COPY requirements.txt /app/
RUN pip install -r requirements.txt

COPY . /app
EXPOSE 8000
CMD ["uvicorn", "app.adapters.api.fastapi_app:app", "--host", "0.0.0.0", "--port", "8000"]
# End of /docker/Dockerfile