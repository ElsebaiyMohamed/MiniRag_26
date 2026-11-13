# Configuration

All application settings are environment variables, loaded by `src/helpers/config.py` (pydantic-settings). Names are case-sensitive and spelled exactly as in the code, including historical spellings such as `FILE_ALLOWED_EXTENTIONS` and `DEAFAULT_MAX_OUTPUT_TOKENS`. Do not "fix" them in your env files.

Real environment variables take precedence over values in a `.env` file.

## Config files

The repository ships example configuration files, not populated secret files. Real files hold secrets and are git-ignored, so you create them by copying:

| Real file (you create it) | Copy from | Used by |
|---|---|---|
| `src/.env.app` | `src/.env.example.app` | Local development |
| `docker/envv/.env.app` | `docker/envv/.env.example.app` | `fastapi` container |
| `docker/envv/.env.app.postgres` | `docker/envv/.env.example.postgres` | `pgvector` container |
| `docker/envv/.env.app.postgresexporter` | `docker/envv/.env.example.postgresexporter` | `postgres-exporter` container |
| `docker/envv/.env.app.grafana` | `docker/envv/.env.example.grafana` | `grafana` container |
| `src/models/db_schemas/minirag26/alembic.ini` | `src/models/db_schemas/minirag26/alembic.ini.example` | Alembic, local development |
| `docker/minirag/alembic.ini` | `docker/minirag/alembic.example.ini` | Alembic inside the Docker image |

The application settings file is anchored to `src/.env.app`, regardless of the current working directory. Real environment variables override values from that file.

### Database credentials must match everywhere

In the Docker setup the same database credentials appear in four places. Keep them identical:

| File | Keys |
|---|---|
| `envv/.env.app.postgres` | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` |
| `envv/.env.app.postgresexporter` | `DATA_SOURCE_USER`, `DATA_SOURCE_PASS` |
| `envv/.env.app` | `POSTGRES_USERNAME`, `POSTGRES_PASSWORD`, `POSTGRES_MAIN_DATABASE` |
| `minirag/alembic.ini` | `sqlalchemy.url` |

Inside the Docker network the database host is `pgvector` and the port is `5432`.

## Reference

"Required" means the application fails to start if the variable is missing. A value may be an empty string where noted.

### Application

| Variable | Required | Description |
|---|---|---|
| `APP_NAME` | yes | Returned by `GET /` |
| `APP_VERSION` | yes | Returned by `GET /` |
| `APP_DESCRIPTION` | yes | Returned by `GET /` |

### File handling

| Variable | Required | Description |
|---|---|---|
| `FILE_ALLOWED_EXTENTIONS` | yes | JSON list of allowed upload **MIME types**, e.g. `["application/pdf", "text/plain"]`. Files are matched on the content type sent by the client |
| `FILE_MAX_SIZE_IN_MB` | yes | Maximum upload size in megabytes |
| `FILE_DEAFAULT_CHINK_SIZE` | yes | Bytes read per iteration while streaming an upload to disk (for example `256000`) |

If you run behind the bundled Nginx, its own upload limit also applies. See [Deployment](Deployment.md#nginx).
### Document processing

| Variable                     | Required | Default | Description                                                                                                        |
|------------------------------|----------|---------|--------------------------------------------------------------------------------------------------------------------|
| `PROCESSING_MAX_CONCURRENCY` | no       | `2`     | Maximum number of documents being loaded and split concurrently per application worker. Must be greater than zero. |

Document loading and chunking run in worker threads using `asyncio.to_thread()`.
An asyncio semaphore limits concurrent processing operations.

The limit applies independently to each application worker. For example,
two workers configured with `PROCESSING_MAX_CONCURRENCY=2` can process
up to four documents concurrently.

### PostgreSQL

| Variable | Required | Description |
|---|---|---|
| `POSTGRES_USERNAME` | yes | Database user |
| `POSTGRES_PASSWORD` | yes | Database password |
| `POSTGRES_HOST` | yes | `pgvector` in Docker, `localhost` for local development |
| `POSTGRES_PORT` | yes | `5432` unless you changed it |
| `POSTGRES_MAIN_DATABASE` | yes | Database name, for example `minirag26` |

### Vector database

| Variable | Required | Description |
|---|---|---|
| `VECTORDB_BACKEND` | yes | `PGVECTOR`. Any other value fails at startup |
| `VECTORDB_BACKEND_LITERAL` | no | Informational list of valid backends. The application does not read it |
| `VECTOR_DB_DISTANCE_METRIC` | no | Distance metric; defaults to `cosine`. `dot` is also supported. |
| `VECTOR_DB_PGVEC_INDEX_THRESHOLD` | yes | Minimum number of rows in a collection before an HNSW index is created on it. Below the threshold, searches scan exactly |

### LLM providers

| Variable                         | Required        | Description                                                                              |
|----------------------------------|-----------------|------------------------------------------------------------------------------------------|
| `GENERATION_BACKEND`             | yes             | Provider used for answers: `COHERE` or `OPENAI`                                          |
| `EMBEDDING_BACKEND`              | yes             | Provider used for embeddings: `COHERE` or `OPENAI`. May differ from `GENERATION_BACKEND` |
| `COHERE_API_KEY`                 | only for Cohere | Non-empty Cohere key when either backend is `COHERE`                                     |
| `OPENAI_API_KEY`                 | only for OpenAI | Non-empty key when either backend is `OPENAI`; Ollama accepts any non-empty value        |
| `OPENAI_API_URL`                 | no              | Base URL of an OpenAI-compatible API. Empty or unset uses the official OpenAI endpoint   |
| `GENERATION_MODEL_ID`            | yes in practice | Model used for answers                                                                   |
| `EMBEDDING_MODEL_ID`             | yes in practice | Model used for embeddings                                                                |
| `EMBEDDING_MODEL_SIZE`           | yes in practice | Output dimension of the embedding model. **Must match the model exactly**                |
| `LLM_REQUEST_TIMEOUT_SEC`        | no              | Request timeout in seconds for LLM provider calls (defaults to `60.0`)                   |
| `INPUT_DEFAULT_MAX_CHAR`         | no              | Passed to providers, but prompt truncation is currently disabled, so it has no effect    |
| `DEAFAULT_MAX_OUTPUT_TOKENS`     | no              | Maximum tokens generated per answer                                                      |
| `GENERATION_DEFAULT_TEMPERATURE` | no              | Sampling temperature for answers (the example uses `0.1`)                                |

The `*_BACKEND` values are the uppercase names of the provider enum, so `COHERE` and `OPENAI` are the only valid ones.

### Prompt language

| Variable | Required | Description |
|---|---|---|
| `PRIMARY_LANG` | no (default `en`) | Prompt template language, one of the folders in `src/stores/llm/templates/locales/` (`en`, `ar`) |
| `DEFAULT_LANG` | no (default `en`) | Fallback when `PRIMARY_LANG` has no folder or a missing template |

The templates also instruct the model to answer in the language of the question, so `PRIMARY_LANG` mostly affects the instructions the model sees, not the reply language.

## Embedding dimensions

`EMBEDDING_MODEL_SIZE` is used to create the vector column or collection. A mismatch with the real model output makes inserts fail. Common values, for reference (provider catalogs change, so confirm in the provider's documentation):

| Provider | Model | Dimension |
|---|---|---|
| Cohere | `embed-english-light-v3.0` | 384 |
| Cohere | `embed-multilingual-light-v3.0` | 384 |
| Cohere | `embed-multilingual-v3.0` | 1024 |
| OpenAI | `text-embedding-3-small` | 1536 |
| OpenAI | `text-embedding-3-large` | 3072 |
| Ollama | `nomic-embed-text` | 768 |
| Ollama | `bge-m3` | 1024 |

If you change `EMBEDDING_MODEL_ID` or `EMBEDDING_MODEL_SIZE` for a project that is already indexed, re-index with `"do_reset": 1` on `POST /api/v1/nlp/index/push/{project_id}` so the collection is recreated. Vectors from different models are not comparable, even at the same dimension.

For Arabic content, use a multilingual embedding model. An English-only model gives poor retrieval.

## Examples by provider combination

Only the changed keys are shown. Everything else stays as in your example env file.

### Cohere + pgvector

```ini
VECTORDB_BACKEND="PGVECTOR"
VECTOR_DB_DISTANCE_METRIC="cosine"
GENERATION_BACKEND="COHERE"
EMBEDDING_BACKEND="COHERE"
COHERE_API_KEY="<your key>"
GENERATION_MODEL_ID="command-r-plus-08-2024"
EMBEDDING_MODEL_ID="embed-multilingual-light-v3.0"
EMBEDDING_MODEL_SIZE=384
```

### OpenAI + pgvector

```ini
VECTORDB_BACKEND="PGVECTOR"
GENERATION_BACKEND="OPENAI"
EMBEDDING_BACKEND="OPENAI"
OPENAI_API_KEY="<your key>"
OPENAI_API_URL=""
GENERATION_MODEL_ID="<chat model>"
EMBEDDING_MODEL_ID="text-embedding-3-small"
EMBEDDING_MODEL_SIZE=1536
```

### Fully local with Ollama

```ini
GENERATION_BACKEND="OPENAI"
EMBEDDING_BACKEND="OPENAI"
OPENAI_API_KEY="ollama"
OPENAI_API_URL="http://localhost:11434/v1"
GENERATION_MODEL_ID="<model you pulled>"
EMBEDDING_MODEL_ID="bge-m3"
EMBEDDING_MODEL_SIZE=1024
```

When the API runs inside Docker, `localhost` refers to the container. Use `http://host.docker.internal:11434/v1`. See [Troubleshooting](Troubleshooting.md#ollama-is-unreachable-from-docker).

### Mixed: cloud embeddings, local generation

Providers are chosen independently for generation and embeddings, but both OpenAI-compatible settings (`OPENAI_API_URL`) and the Cohere key are global:

```ini
GENERATION_BACKEND="OPENAI"
OPENAI_API_URL="http://localhost:11434/v1"
OPENAI_API_KEY="ollama"
GENERATION_MODEL_ID="<local model>"

EMBEDDING_BACKEND="COHERE"
COHERE_API_KEY="<your key>"
EMBEDDING_MODEL_ID="embed-multilingual-v3.0"
EMBEDDING_MODEL_SIZE=1024
```

Using `OPENAI` for both roles means both talk to the same `OPENAI_API_URL`.

### Arabic-first

```ini
PRIMARY_LANG="ar"
DEFAULT_LANG="en"
EMBEDDING_MODEL_ID="<multilingual embedding model>"
EMBEDDING_MODEL_SIZE=<its dimension>
```

## Adding a new setting

1. Add the field to `Settings` in `src/helpers/config.py`.
2. Add it to `../src/.env.example.app` and `docker/envv/.env.example.app`.
3. Document it in this file.
4. Mention it in `Changelog.md` under *Unreleased*.
