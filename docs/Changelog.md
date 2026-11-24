# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Add the application-layer `ProcessAsset` use case to coordinate per-asset document loading, chunking, and persistence.
- Add `LocalAssetFileResolver` to resolve stored asset paths safely and prevent path traversal.
- Add transactional asset processing persistence to insert chunks and update the asset status to `CHUNKED` atomically.
- Add unit, adapter, repository integration, and API workflow tests for the asset processing flow.

### Changed

- Integrate `ProcessAsset` into the data processing route while preserving the existing API response contract and per-asset failure behavior.
- Refactor file upload handling into an application-layer `IngestFile` use case, separating upload validation, file storage, and asset creation from the FastAPI route.
- Introduce storage and repository ports with infrastructure adapters for local file storage and SQLAlchemy persistence.
- Add unit tests for the ingestion use case using fake dependencies.

## [1.3.0]  - 2026-11-23

### Added

- Add Markdown ingestion support for `.md` and `.markdown` files, including encoding detection, YAML front matter removal, HTML comment stripping, and preservation of Markdown structure (`#63`).
- Add Markdown loader, registry, upload validation, and end-to-end workflow tests covering processing, indexing, and ranked search (`#63`).
- Add dedicated PDF loader tests covering multi-page extraction, encrypted PDFs, corrupted PDFs, image-only PDFs, and empty-text pages (`#62`).
- Add chunking abstraction package under `src/ingestion/chunkers/` (`__init__.py`, `base.py`, `default.py`, `factory.py`) with `DefaultChunker` reproducing newline-based splitting behavior (`#101`).
- Integrate the chunker abstraction and factory into `ProcessController.process_file_content`, `src/main.py`, `src/models/schemas/data.py`, and `src/routes/data.py` (`#101`).
- Update chunker and controller test suites in `tests/test_chunker.py` and `tests/test_process_controller.py` to use `LoadedDocument` and `process_file_content` (`#101`).
- added bug report and feature request templates


### Changed

- Extend the shared loader registry and upload validation to support Markdown MIME types and filename extensions (`#63`).
- Update README documentation to reflect Markdown ingestion support (`#63`).
- Replace LangChain-based TXT and PDF loading with native loaders: Python standard-library UTF-8 reading for TXT files and direct PyMuPDF extraction for PDFs (`#62`).
- Extract PDF content page by page while preserving page-level metadata and normalized creation/modification dates (`#62`).
- Update the golden fixture generator to use the application's native TXT and PDF loaders (`#62`).
- Replace `ProcessController.simple_text_spliter` usage with `ProcessController.process_file_content` and factory-selected chunkers while preserving existing splitting and metadata behavior (`#101`).
- Centralized document format support in an injectable loader registry shared by upload validation and processing.
- Validate upload filename extensions and MIME types as a matching pair against registered loaders.
- Retained `FILE_ALLOWED_EXTENTIONS` as an additional MIME-type allowlist.


### Removed

- Remove LangChain and LangChain Community dependencies; document loading no longer relies on LangChain (`#62`).
- Split text directly in `ProcessController.simple_text_spliter`.


## [1.2.0]  - 2026-11-14

### Documentation

- Synchronize API endpoint documentation with actual route response signals and HTTP status codes.
- Add a complete response signal reference and troubleshooting table.
- Add automated tests to detect API documentation drift against the response enum and OpenAPI schema.

### Added

- Offloaded synchronous document loading and chunking to worker threads using `asyncio.to_thread()`.
- Added configurable per-worker document processing concurrency through `PROCESSING_MAX_CONCURRENCY`.
- Added Prometheus document processing duration histogram with file type and outcome labels.
- Added tests for event-loop responsiveness, processing concurrency, and combined file processing.
- Unified `LLMResult` contract for all LLM provider generation and embedding calls, including latency and token usage
  telemetry (`prompt_tokens`, `completion_tokens`, `total_tokens`).
- Shared `_safe_call` wrapper in `LLMInterface` enforcing configurable request timeouts (`LLM_REQUEST_TIMEOUT_SEC`),
  latency measurement, and sanitized error logging.
- Provider-level `_parse_response` handlers in `OpenAiProvider` and `CohereProvider` to normalize SDK response shapes
  and token metrics.
- Per-asset upload, chunking, and indexing status tracking with incremental processing and indexing.
- API documentation for the `UPLOADED` → `CHUNKED` → `INDEXED` lifecycle, reset behavior, updated process response fields, indexing result details, and no-pending-work signals.
- Opt-in answer diagnostics: set `debug` to `true` to include the prompt and chat history in an answer response.
- Automated unit, API workflow, and pgvector integration tests, with CI coverage for the test suite.

### Changed

- Use `pyproject.toml` as the single source of truth for the application version.
- Expose the application version through FastAPI metadata and `GET /version`.
- Deprecate and ignore the `APP_VERSION` environment setting.
- NLP routes (`/index/push`, `/index/info`, `/index/search`, `/index/answer`) now map upstream LLM and vector store
  failures to HTTP `502 Bad Gateway` and return standardized `telemetry` metadata.
- Processing reset rebuilds chunks for all project files, and PgVector removes vectors associated with deleted chunks.
- Indexing reset recreates the project's vector collection and indexes eligible chunked assets.
- Indexing reports per-file and per-chunk outcomes; an asset with any failed chunk is treated as failed and its inserted vectors are removed.
- Projects are created by upload; other operations no longer silently create a project when given an unknown ID.
- Upload validation checks the declared MIME type, filename extension, and configured size limit.
- LLM provider calls use asynchronous SDK clients.
- Docker's multi-worker API metrics use Prometheus multiprocess collection.
- Refreshed locked dependencies and declared SQLAlchemy's asyncio extra.


## [1.1.0] - 2026-10-11

First tagged release. It builds on the code from the original mini-RAG course and adds a production-oriented stack, documentation, and a roadmap.

### Added

- Document upload for `.txt` and `.pdf` files (10 MB by default) with per-project storage.
- Chunking endpoint with a line-aware text splitter and configurable chunk size.
- Indexing endpoint that embeds chunks and stores vectors in pgvector, with an automatic HNSW index once a collection passes a configurable size.
- Semantic search and retrieval-augmented answering endpoints, with English and Arabic prompt templates.
- Pluggable LLM providers: Cohere and any OpenAI-compatible API, including local models through Ollama.
- PostgreSQL storage for projects, assets, and chunks, with Alembic migrations.
- Docker Compose stack: FastAPI, Nginx, PostgreSQL with pgvector, Prometheus, Grafana, node-exporter, and postgres-exporter.
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
