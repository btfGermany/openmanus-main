# OpenManus API Service Migration Document

## Summary

This document describes the transformation of the OpenManus codebase into a production-ready, headless AI Agent API service.

---

## Files Created

### API Layer (`/api/`)

| File | Purpose |
|------|---------|
| `api/__init__.py` | API package marker |
| `api/main.py` | FastAPI application entry point |
| `api/models.py` | Pydantic request/response models |
| `api/config.py` | API-specific configuration |
| `api/routes/__init__.py` | Routes package marker |
| `api/routes/tasks.py` | Task CRUD and streaming endpoints |
| `api/routes/health.py` | Health check endpoints |
| `api/routes/admin.py` | Admin API key management |
| `api/core/__init__.py` | Core package marker |
| `api/core/storage.py` | Task storage and workspace management |
| `api/core/events.py` | Redis Pub/Sub event bus for SSE |
| `api/core/auth.py` | API key store and rate limiter |
| `api/core/wrapper.py` | OpenManus agent wrapper |
| `api/Dockerfile` | API service container |
| `api/requirements.txt` | Python dependencies |
| `api/config.toml` | API configuration |

### Worker (`/worker/`)

| File | Purpose |
|------|---------|
| `worker/__init__.py` | Worker package marker |
| `worker/worker.py` | RQ background worker |

### Configuration Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Multi-container deployment |
| `nginx.conf` | Reverse proxy configuration |
| `ANALYSIS.md` | Pre-implementation analysis document |

---

## Files Preserved (Untouched)

All existing OpenManus files remain unchanged:

- `main.py` - Agent entry point
- `run_flow.py` - Flow-based execution
- `app/agent/*.py` - Agent implementations
- `app/tool/*.py` - Tool implementations
- `app/config.py` - Core configuration
- `config/config.toml` - Agent configuration

---

## API Endpoints

### Task Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/tasks` | Submit a new task |
| `GET` | `/api/v1/tasks/{task_id}` | Get task status |
| `GET` | `/api/v1/tasks/{task_id}/result` | Get task result |
| `GET` | `/api/v1/tasks/{task_id}/stream` | SSE event stream |
| `GET` | `/api/v1/tasks/{task_id}/files` | List workspace files |
| `GET` | `/api/v1/tasks/{task_id}/files/{path}` | Download file |

### Health Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Full health check |
| `GET` | `/api/v1/ready` | Readiness probe |
| `GET` | `/api/v1/live` | Liveness probe |

### Admin Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/admin/keys` | Create API key |
| `GET` | `/admin/keys` | List API keys |
| `DELETE` | `/admin/keys/{key_id}` | Revoke API key |
| `GET` | `/admin/usage` | Usage statistics |

---

## SSE Event Types

| Event | Description |
|-------|-------------|
| `plan_created` | Initial execution plan |
| `iteration_start` | Iteration started |
| `tool_call` | Tool execution started |
| `tool_result` | Tool execution completed |
| `observation` | Execution output |
| `error` | Error occurred |
| `plan_update` | Plan step status |
| `final_result` | Task completed |
| `done` | Task finished |

---

## Usage Example

```bash
# Submit task
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "X-API-Key: sk-manus-abc123" \
  -H "Content-Type: application/json" \
  -d '{"goal": "Research GPU prices", "mode": "flow"}'

# Stream events
curl -N -H "X-API-Key: sk-manus-abc123" \
  http://localhost:8000/api/v1/tasks/{task_id}/stream
```

---

## Deployment

```bash
# Start all services
docker-compose up -d

# Check health
curl http://localhost:8000/api/v1/health

# View logs
docker-compose logs -f api
```

---

## Backward Compatibility

The existing OpenManus CLI continues to work:

```bash
python main.py --prompt "Your task"
python run_flow.py
```

The API layer is **additive** and doesn't modify the original runtime.

---

*Generated: 2026-05-13*