# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [1.1.0] - 2026-10-11

First tagged release. It builds on the code from the original mini-RAG course and adds a production-oriented stack, documentation, and a roadmap.

### Added

- Document upload for `.txt` and `.pdf` files (10 MB by default) with per-project storage.
- Chunking endpoint with a line-aware text splitter and configurable chunk size.
- Indexing endpoint that embeds chunks and stores vectors in pgvector or Qdrant, with an automatic HNSW index once a collection passes a configurable size.
- Semantic search and retrieval-augmented answering endpoints, with English and Arabic prompt templates.
- Pluggable LLM providers: Cohere and any OpenAI-compatible API, including local models through Ollama.
- PostgreSQL storage for projects, assets, and chunks, with Alembic migrations.
- Docker Compose stack: FastAPI, Nginx, PostgreSQL with pgvector, Qdrant, Prometheus, Grafana, node-exporter, and postgres-exporter.
- Prometheus request metrics (`http_requests_total`, `http_request_duration_seconds`) exposed at `/metrics`.
- Documentation: README with architecture diagrams, tech stack, and roadmap, plus `docs/` guides for configuration, the API (with an exported OpenAPI schema), adding a provider, deployment, monitoring, troubleshooting, and development.

### Changed

- Application storage moved from MongoDB to PostgreSQL.
- `project_id` is now an integer instead of a string.
- The upload response returns the stored asset name instead of the asset ID.
- Settings are read from `.env.app`.

### Fixed

- OpenAI-compatible provider: chat responses and batch embeddings are now parsed correctly, which also makes Ollama work.
- Example environment and Alembic files use consistent database credentials and port.

### Removed

- Celery, Flower, and Postman collection references from the README.

[1.1.0]: https://github.com/ElsebaiyMohamed/MiniRag_26/releases/tag/minirag26-postgresql-pgvector-v2
