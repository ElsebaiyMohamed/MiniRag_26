# API reference

Base URL: `http://localhost:8000` (or `http://localhost` through Nginx).

- Interactive docs (Swagger UI): `/docs`
- Machine-readable schema: [`openapi.json`](openapi.json) in this folder, also served live at `/openapi.json`

## Conventions

**Projects.** Every data and NLP endpoint takes an integer `{project_id}`. A project is created implicitly the first time an ID is used, and each project has its own files, chunks, and vector collection. A typo in the ID therefore targets a new, empty project instead of returning an error.

**Signals.** Responses carry a `signal` string that describes the outcome. Clients can match on it. Signals are returned verbatim, including their current spelling (for example `file chuncking success`), so treat changing one as a breaking change.

**Status codes.**

| Code | Meaning |
|---|---|
| `200` | Success |
| `400` | The request was understood but could not be completed. See the `signal` |
| `422` | The request body or parameters failed validation (FastAPI default format) |
| `500` | Unexpected server error, for example a failed file write |

**Request bodies** are JSON unless noted. Flags such as `do_reset` are integers: `0` or `1`.

## Typical flow

```text
upload  ->  process  ->  index/push  ->  index/search  or  index/answer
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | App name, version, description |
| `GET` | `/metrics` | Prometheus metrics (not in the OpenAPI schema) |
| `POST` | `/api/v1/data/upload/{project_id}` | Upload a file |
| `POST` | `/api/v1/data/process/{project_id}` | Chunk the project's files |
| `POST` | `/api/v1/nlp/index/push/{project_id}` | Embed chunks and store the vectors |
| `GET` | `/api/v1/nlp/index/info/{project_id}` | Vector collection information |
| `POST` | `/api/v1/nlp/index/search/{project_id}` | Semantic search |
| `POST` | `/api/v1/nlp/index/answer/{project_id}` | RAG answer |

---

## `GET /`

```bash
curl http://localhost:8000/
```

```json
{
  "app_name": "MiniRag_26",
  "version": "0.1",
  "description": "Question Answering System"
}
```

---

## `POST /api/v1/data/upload/{project_id}`

Uploads one file as `multipart/form-data` with the field name `file`. Allowed types and the size limit come from `FILE_ALLOWED_EXTENTIONS` and `FILE_MAX_SIZE_IN_MB`. See [Configuration](configuration.md).

```bash
curl -X POST http://localhost:8000/api/v1/data/upload/1 \
  -F "file=@document.pdf;type=application/pdf"
```

**200**

```json
{
  "signal": "file upload successed",
  "file_id": "k3_document.pdf"
}
```

`file_id` is the stored file name (a random prefix plus the cleaned original name).

**Errors**

| Status | `signal` | Cause |
|---|---|---|
| `400` | `file type not supported` | Content type not allowed |
| `400` | `file size exceeded` | File larger than the configured maximum |
| `500` | `file upload failed` | The file could not be written to disk |

---

## `POST /api/v1/data/process/{project_id}`

Loads every uploaded file in the project and splits it into chunks, stored in PostgreSQL.

**Body**

| Field | Type | Default | Description |
|---|---|---|---|
| `chunk_size` | integer | `100` | Target chunk length in characters. The default is small, so set it explicitly |
| `overlap_size` | integer | `20` | Accepted but not applied yet |
| `do_reset` | integer | `0` | `1` deletes the project's existing chunks first |

```bash
curl -X POST http://localhost:8000/api/v1/data/process/1 \
  -H "Content-Type: application/json" \
  -d '{"chunk_size": 1000, "do_reset": 1}'
```

**200**

```json
{
  "signal": "file chuncking success",
  "no_files": 2,
  "no_files_success": 2,
  "no_records": 148
}
```

`no_files_success` counts files that could be loaded. `no_records` is the number of chunks created.

**Errors**

| Status | `signal` | Cause |
|---|---|---|
| `400` | `project is empty` | No files uploaded for this project |
| `400` | `file chuncking failed` | A file produced no chunks. The response also includes `file_id` |

---

## `POST /api/v1/nlp/index/push/{project_id}`

Embeds the project's chunks and writes the vectors to the vector store.

**Body**

| Field | Type | Default | Description |
|---|---|---|---|
| `do_reset` | integer | `0` | `1` drops and recreates the project's vector collection first. Required after changing the embedding model |

```bash
curl -X POST http://localhost:8000/api/v1/nlp/index/push/1 \
  -H "Content-Type: application/json" \
  -d '{"do_reset": 1}'
```

**200**

```json
{ "signal": "insert into vector database success" }
```

**Errors**

| Status | `signal` | Cause |
|---|---|---|
| `400` | `failed to insert into vector database` | Embedding or insert failed, or there was nothing to index |

---

## `GET /api/v1/nlp/index/info/{project_id}`

Returns information about the project's vector collection. Useful to confirm that indexing worked.

```bash
curl http://localhost:8000/api/v1/nlp/index/info/1
```

**200** (pgvector backend)

```json
{
  "signal": "collection information retrived successfly",
  "collection_info": {
    "table_info": {
      "schemaname": "public",
      "tablename": "pgvector_collection_1",
      "tableowner": "postgres",
      "tablespace": null,
      "hasindexes": false
    },
    "record_count": 148
  }
}
```

The shape of `collection_info` depends on the vector store. 

---

## `POST /api/v1/nlp/index/search/{project_id}`

Semantic search over the project's chunks. Returns the chunks most similar to the text, without calling a generation model.

**Body**

| Field | Type | Default | Description |
|---|---|---|---|
| `text` | string | required | The query |
| `limit` | integer | `10` | Number of chunks to return |

```bash
curl -X POST http://localhost:8000/api/v1/nlp/index/search/1 \
  -H "Content-Type: application/json" \
  -d '{"text": "What is the refund policy?", "limit": 3}'
```

**200**

```json
{
  "signal": "vectordb search success",
  "result": [
    { "text": "Refunds are issued within 14 days of ...", "score": 0.83 },
    { "text": "To request a refund, contact ...", "score": 0.79 }
  ]
}
```

Results are sorted best first. A higher `score` means more similar.

**Errors**

| Status | `signal` | Cause |
|---|---|---|
| `400` | `vectordb search error` | The collection does not exist (nothing pushed), or embedding the query failed |

---

## `POST /api/v1/nlp/index/answer/{project_id}`

Retrieval-augmented answer. The question is embedded, the closest chunks are retrieved, a prompt is built from the localized template, and the generation model answers using only those documents.

**Body**: same as search (`text`, `limit`).

```bash
curl -X POST http://localhost:8000/api/v1/nlp/index/answer/1 \
  -H "Content-Type: application/json" \
  -d '{"text": "What is the refund policy?", "limit": 5}'
```

**200**

```json
{
  "signal": "rag answer success",
  "answer": "Refunds are issued within 14 days ...",
  "full_prompt": "## Document No: 1\n### Content: ...\n\n## Document No: 2 ...",
  "chat_history": [
    { "role": "system", "content": "You are an assistant to generate a response ..." }
  ]
}
```

| Field | Description |
|---|---|
| `answer` | The model's reply |
| `full_prompt` | The documents and question exactly as sent to the model. Useful for debugging retrieval quality |
| `chat_history` | The messages sent before the final question. Depending on the provider, the final user message may also appear here |

**Errors**

| Status | `signal` | Cause |
|---|---|---|
| `400` | `rag answer error` | Nothing was retrieved, or the generation provider returned no text |

---

## Regenerating `openapi.json`

The schema is generated from the application, so regenerate it whenever endpoints or models change. From the repository root:

```bash
cd src
uv run python -c "import json; from main import app; print(json.dumps(app.openapi(), indent=2))" > ../docs/openapi.json
```

This does not need a running database, because it only builds the schema and does not start the application.
