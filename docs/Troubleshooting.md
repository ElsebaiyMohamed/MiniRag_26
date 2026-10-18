# Troubleshooting

Each entry lists the symptom, the cause, and the fix. Start with the logs:

```bash
docker compose logs -f fastapi      # Docker (run from docker/)
```

For local development, read the `uvicorn` terminal output. Application errors are logged under the `uvicorn` and `uvicorn.error` loggers.

Two endpoints help narrow things down quickly:

- `GET /` confirms the API is up and shows the loaded app name and version.
- `GET /api/v1/nlp/index/info/{project_id}` shows whether a project's vector collection exists and how many records it holds.

## Setup and startup

### `docker compose build` fails: `alembic.ini` not found

**Cause:** the repository ships `docker/minirag/alembic.example.ini`, not the real file. The Dockerfile copies `docker/minirag/alembic.ini`.

**Fix:**

```bash
cd docker
cp minirag/alembic.example.ini minirag/alembic.ini
```

Then set `sqlalchemy.url` inside it. See [Configuration](configuration.md#config-files).

### `compose` complains that an env file is missing

**Cause:** the real `envv/.env.*` files were not created from the examples.

**Fix:** copy each `envv/.env.example.<name>` to `envv/.env.<name>`. The full list is in [Configuration](configuration.md#config-files).

### API fails at startup with `ValidationError: Field required`

**Fix:** run `uvicorn` from `src/`, and compare your `.env.app` against `src/.env.example`. All keys must exist. Keys for unused providers (such as `COHERE_API_KEY`) may be empty strings but must be present.

### API fails at startup right after the vector database step

**Cause:** `VECTORDB_BACKEND` is empty or not one of `PGVECTOR` or `QDRANT`, so no vector store could be created.

**Fix:** set `VECTORDB_BACKEND` exactly to `PGVECTOR` or `QDRANT` (uppercase).

**Cause:** `GENERATION_BACKEND` is empty or not one of `OPENAI` or `COHERE`, so no 
llms store could be created.

**Fix:** set `GENERATION_BACKEND` exactly to `OPENAI` or `COHERE` (uppercase).

### `alembic upgrade head` fails with `No module named 'schemas'`

**Cause:** Alembic was run from the wrong folder. Its `env.py` imports `schemas` relative to the migrations folder.

**Fix:**

```bash
cd src/models/db_schemas/minirag26
uv run alembic upgrade head
```

### Connection refused or `password authentication failed` for Postgres

**Cause and fix, by environment:**

- **Docker:** `POSTGRES_HOST` must be `pgvector` and `POSTGRES_PORT` must be `5432`. The credentials in `.env.app`, `.env.postgres`, `.env.postgresexporter`, and `alembic.ini` must be identical.
- **Local development:** `POSTGRES_HOST=localhost`, and Postgres must be running and reachable.
- **Changed the password after first start:** the Postgres volume keeps the old credentials. Either change the password inside the database, or remove the volume (this **deletes all data**): `docker compose down -v`.

### Log warning: `Vector extension setup`

**Cause:** the application runs `CREATE EXTENSION vector` at startup and the extension is unavailable or the user lacks permission.

**Fix:** use a Postgres image or install that ships pgvector (the Compose file uses the `pgvector/pgvector` image). With your own Postgres, install pgvector and run `CREATE EXTENSION vector;` as a superuser.

### Build errors installing `psycopg2` on a local machine

**Cause:** missing system build dependencies.

**Fix (Debian/Ubuntu):**

```bash
sudo apt update
sudo apt install libpq-dev gcc python3-dev
```

### A port is already in use

The stack publishes these host ports: `80` (Nginx), `8000` (API), `5432` (Postgres), `6333` and `5334` (Qdrant), `3000` (Grafana), `9090` (Prometheus), `9100` (node-exporter), `9187` (postgres-exporter).

**Fix:** stop the process using the port, or change the left side of the mapping in `docker/docker-compose.yml`, for example `"5433:5432"` to expose Postgres on host port `5433` while the container keeps `5432`. Do not change the container-side port or the `POSTGRES_PORT` used inside the Docker network.

## Uploading and processing

### Upload returns `file type not supported`

**Cause:** the type is not in `FILE_ALLOWED_EXTENTIONS`, or the client sent a different content type (`application/octet-stream` is common).

**Fix:** set the content type explicitly:

```bash
curl -X POST http://localhost:8000/api/v1/data/upload/1 \
  -F "file=@document.pdf;type=application/pdf"
```

Only `.txt` and `.pdf` are supported today.

### Upload returns `file size exceeded`

**Cause:** the file is larger than `FILE_MAX_SIZE_IN_MB`.

**Fix:** use a smaller file, or raise the limit. If you go through Nginx, raise its limit too (next entry).

### Upload through port 80 fails with `413 Request Entity Too Large`

**Cause:** Nginx rejects request bodies above its own limit, which is 1 MB unless configured, before the API sees them. Uploading directly to port `8000` works.

**Fix:** add `client_max_body_size` to `docker/nginx/default.conf` so it is at least as large as `FILE_MAX_SIZE_IN_MB`, then restart Nginx. See [Deployment](deployment.md#nginx).

### Process returns `project is empty`

**Cause:** no files were uploaded for that `project_id`.

**Fix:** upload at least one file to the same `project_id` first.

### Process returns `file chuncking failed`

**Cause:** a file produced no chunks. Typical reasons are a scanned PDF with no text layer, an empty file, or a `chunk_size` far larger than the document.

**Fix:** open the file and confirm it contains selectable text. Scanned documents need OCR, which is on the [roadmap](../README.md#roadmap).

### Chunks look wrong or very small

**Cause:** `chunk_size` defaults to `100` characters, which is tiny. `overlap_size` is accepted but not applied yet.

**Fix:** pass an explicit `chunk_size`, for example a few hundred to about a thousand characters, and tune it by checking search results.

## Indexing

### Push fails with a dimension error

Typical message from Postgres: `expected N dimensions, not M`.

**Cause:** `EMBEDDING_MODEL_SIZE` does not match what the embedding model returns, or the model was changed after the collection was created. The collection is created once, with the dimension that was configured at that time.

**Fix:**

1. Set `EMBEDDING_MODEL_ID` and `EMBEDDING_MODEL_SIZE` to a matching pair. See [the dimension table](configuration.md#embedding-dimensions).
2. Restart the API.
3. Re-index with `"do_reset": 1`:

```bash
curl -X POST http://localhost:8000/api/v1/nlp/index/push/1 \
  -H "Content-Type: application/json" -d '{"do_reset": 1}'
```

### Push returns `failed to insert into vector database`

**Cause:** embedding failed (invalid key, unknown model name, provider outage) or the insert failed.

**Fix:** check the API log for the provider error. Verify the API key, `GENERATION_BACKEND` and `EMBEDDING_BACKEND` spelling (uppercase), and the model IDs.

### Nothing is indexed after a push

**Cause:** the project has no chunks yet. Indexing reads the chunks created by the process step. Projects are created implicitly the first time an ID is used, so a typo in `project_id` silently targets a new, empty project.

**Fix:** run upload, then process, then push, all with the same `project_id`. Check the result with `GET /api/v1/nlp/index/info/{project_id}`.

## Search and answers

### Search returns `vectordb search error`

**Cause:** the collection does not exist (nothing was pushed), or the query embedding failed.

**Fix:** call `GET /api/v1/nlp/index/info/{project_id}`. If it reports no collection or zero records, push first.

### Answer returns `rag answer error`

**Cause:** retrieval found nothing, or the generation provider returned no text.

**Fix:** confirm search works for the same question and project. Then check the generation model ID, API key, `OPENAI_API_URL`, and the API log.

### Answers are in the wrong language or ignore the documents

**Cause:** the retrieved chunks are irrelevant, or the embedding model does not cover the document language.

**Fix:** use a multilingual embedding model for Arabic content, then re-index with `"do_reset": 1`. Inspect what retrieval returned with the search endpoint, and review `full_prompt` in the answer response to see exactly what the model received.

## Models and providers

### Ollama is unreachable from Docker

**Cause:** `localhost` inside the `fastapi` container is the container itself, not your machine.

**Fix:** set:

```ini
OPENAI_API_URL="http://host.docker.internal:11434/v1"
```

On Linux, also add this to the `fastapi` service in `docker/docker-compose.yml`:

```yaml
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

Make sure Ollama listens on an address reachable from the container, and that you pulled both the generation and the embedding model.

### Provider returns authentication or "model not found" errors

**Cause:** wrong key, wrong `*_BACKEND` pairing, or a model name your provider does not offer.

**Fix:** check the key variable for the chosen backend (`COHERE_API_KEY` or `OPENAI_API_KEY`), and confirm the model name in the provider's current model list.

## Vector store

### Multiple workers fail with embedded Qdrant

**Cause:** the Docker image starts several `uvicorn` workers. Embedded (file-based) Qdrant is meant for one process, and a second process opening the same folder is typically rejected.

**Fix:** use `VECTORDB_BACKEND=PGVECTOR`, or run a single worker. See [Deployment](deployment.md#workers-and-the-vector-store).

### Searches are slow on a large project

**Cause:** below `VECTOR_DB_PGVEC_INDEX_THRESHOLD` rows, pgvector scans every row exactly.

**Fix:** lower the threshold so an HNSW index is created sooner, then push again. The index is created after inserts once the row count reaches the threshold.

## Monitoring

### A Prometheus target shows as DOWN

**Fix:** open `http://localhost:9090/targets`. Targets use Docker service names (`fastapi:8000`, `node-exporter:9100`, `postgres-exporter:9187`), so they only resolve inside the Compose network. Confirm the service is running with `docker compose ps`.

### Grafana shows no data

**Fix:** add a Prometheus data source with URL `http://prometheus:9090` (the service name, not `localhost`). See [Monitoring](monitoring.md).

### Cannot log in to Grafana

**Fix:** use the admin user and password from `envv/.env.grafana`. These are applied when the Grafana volume is first created. Changing the file later does not change an existing password. Reset it inside Grafana, or remove the `grafana_data` volume to start over.

## Still stuck?

Open an issue and include: how you run the project (Docker or local), your provider and vector store settings (**without secrets**), the exact request, and the relevant log lines.
