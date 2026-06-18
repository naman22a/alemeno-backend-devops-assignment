# Alemeno Backend DevOPS Assignment

> AI-Powered Transaction Processing Pipeline

## Setting up Dev Environment

### Docker compose dev

```bash
docker compose -f .\docker-compose.dev.yml up
```

### Fast API Server

```bash
fastapi dev
```

### Celery Worker

```bash
celery -A workers.celery_app:celery_app worker -P solo -l info
```
