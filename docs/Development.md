# Development guide

How the code is organized, how to run it while you work on it, and the recipes for the most common changes. For first-time setup, follow the README's [local development](../README.md#local-development-uv) section.

## Project layout

```text
src/
├── main.py            # App creation and startup/shutdown (lifespan)
├── application/       # Application use cases and ports
│   ├── errors.py
│   ├── ports.py
│   └── use_cases/
│       ├── ingest_file.py
│       └── process_asset.py
├── infrastructure/    # Implementations of application ports
│   └── adapters/
│       ├── asset_file_resolver.py
│       ├── file_storage.py
│       └── repositories.py
├── routes/             # HTTP endpoints: base, data, nlp
├── controllers/        # Existing controller-based workflows
├── ingestion/          # Document loading and chunking
│   ├── loaders/        # LoaderRegistry, PdfLoader, TxtLoader, LoadedDocument
│   ├── chunkers/       # Chunker protocol, Chunk, strategies, and factory
│   └── exceptions.py   # Ingestion-related exceptions
├── models/
│   ├── schemas/        # Pydantic request/response models
│   ├── enums/          # Response signals, provider names, asset types
│   ├── db_schemas/     # SQLAlchemy tables and Alembic migrations
│   └── *DataModel.py   # Database access for projects, assets, chunks
├── stores/
│   ├── llm/            # LLM interface, factory, providers, prompt templates
│   └── vectordb/       # Vector store interface, factory, providers
├── helpers/config.py   # Settings
└── utils/metrics.py    # Prometheus middleware
docker/                 # Compose stack, Dockerfile, Nginx, Prometheus, env examples
docs/                   # This documentation
```

### How a request flows

Routes handle HTTP concerns and delegate application operations to the appropriate component.

- **Routes** validate HTTP input, invoke the relevant use case or controller, and build the JSON response with a `signal`.
- **Application layer** contains use cases and port definitions. `IngestFile` coordinates upload validation, project existence, file storage, and asset creation. `ProcessAsset` coordinates per-asset document loading, chunking, and persistence. Both use cases depend on application-level ports rather than FastAPI or SQLAlchemy.
- **Infrastructure adapters** implement application ports. `LocalFileStorage` handles uploaded file storage, `LocalAssetFileResolver` resolves stored asset paths, and SQLAlchemy repositories handle database persistence.
- **Document ingestion** provides the shared `LoaderRegistry` and configured `ChunkerFactory`. The registry resolves the appropriate loader, and the factory provides the configured chunking strategy.
- **Controllers** retain the existing controller-based workflows. `NLPController` handles indexing, semantic search, and RAG answer generation.
- **Clients** (`app.generation_client`, `app.embedding_client`, `app.vectordb_client`, `app.db_client`, and `app.loader_registry`) are initialized during application startup and accessed through `request.app`.

- The architecture diagrams are in the README.

## Running locally

```bash
uv sync
cp src/.env.example.app src/.env.app          # then edit it
```

You need a PostgreSQL database with pgvector. The simplest way is to reuse the one from the Docker stack. Create the env files as described in the README quickstart, then start only the database:

```bash
cd docker
docker compose up -d pgvector
```

It is published on `localhost:5432`, so use `POSTGRES_HOST=localhost` in `src/.env.app`.

Run migrations once, then start the API with auto-reload:

```bash
cd src/models/db_schemas/minirag26
uv run alembic upgrade head

cd ../../..                                # back to src/
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000/docs to try every endpoint from the browser.

## Handy checks while developing

| Goal | How |
|---|---|
| Is the vector collection populated? | `GET /api/v1/nlp/index/info/{project_id}` |
| What did retrieval hand to the model? | Read `full_prompt` in the answer response |
| What chunks match a question? | `POST /api/v1/nlp/index/search/{project_id}` |
| Look inside the database | `docker compose exec pgvector psql -U postgres -d minirag26`, then `\dt` |
| Reset one project's vectors | `index/push` with `"do_reset": 1` |
| Reset one project's chunks | `data/process` with `"do_reset": 1` |
| Wipe everything in Docker | `docker compose down -v` (**deletes all volumes**) |

## Recipes

### Add or change an endpoint

1. Add request and response models in `src/models/schemas/` and export them in `__init__.py`.
2. Add any new outcome strings to `ResponseSignal` in `src/models/enums/ResponseEnums.py`.
3. Put the logic in a controller, and keep the route thin.
4. Add the route to the matching router in `src/routes/`. A new router file must also be included in `main.py`.
5. Update [API reference](Api.md) and regenerate `docs/Openapi.json` (the command is at the bottom of that file).

Signal strings are part of the public API. Changing an existing one is a breaking change and belongs in the changelog.

### Add an application use case

1. Define the use case in `src/application/use_cases/`.
2. Define the required interfaces in `src/application/ports.py`. Keep the use case independent of infrastructure implementations.
3. Add application-specific exceptions to `src/application/errors.py` when needed.
4. Implement the required ports in `src/infrastructure/adapters/`.
5. Wire the use case into the relevant route or application entry point.
6. Add unit tests for the use case using fake or in-memory port implementations, and add API workflow tests for the integration.

Application use cases must not depend on FastAPI or SQLAlchemy. Infrastructure adapters are responsible for database and filesystem operations.

For asset processing, `ProcessAsset` resolves the stored file path, selects a document loader and chunker, and delegates persistence to the asset processing repository. Synchronous document loading and chunking run in a worker thread. The repository handles chunk insertion and the asset status update within one database transaction.

### Add a setting

Follow the steps in [Configuration](Configuration.md#adding-a-new-setting).

### Change the database schema

1. Edit or add a model in `src/models/db_schemas/minirag26/schemas/`, and make sure it is imported in that package's `__init__.py`.
2. Generate a migration:

   ```bash
   cd src/models/db_schemas/minirag26
   uv run alembic revision --autogenerate -m "short description"
   ```

3. **Read the generated file.** Autogenerate misses some changes and can include unwanted ones.
4. Apply it with `uv run alembic upgrade head`.
5. In Docker, migrations run on container start. Rebuild the image so the new migration is included: `docker compose up -d --build`.

The per-project vector tables created by the pgvector provider are not managed by Alembic. They are created at runtime when a project is indexed.

### Add an LLM provider, vector store, or prompt language

See [Adding a provider](Adding%20a%20provider.md).

### Built-in document loaders

The default loader registry currently supports:

| Loader      | Format | Implementation                                         | Output                            |
|-------------|--------|--------------------------------------------------------|-----------------------------------|
| `TxtLoader` | `.txt` | Python standard library (`Path.read_text`) using UTF-8 | One `LoadedDocument` per file     |
| `PdfLoader` | `.pdf` | PyMuPDF (`pymupdf`)                                    | One `LoadedDocument` per PDF page |

Each `LoadedDocument` contains extracted text and metadata. PDF metadata includes the resolved source path, file path, zero-based page number, and total page count. Available PDF creation and modification dates are normalized to ISO format.

PDF handling behavior:

- Encrypted PDFs raise `UnsupportedFile`.
- PDFs that cannot be opened raise `UnsupportedFile`.
- Repaired PDFs with no recoverable pages are rejected.
- Image-only or scanned PDFs are not OCR-processed. Their pages are returned with empty extracted text.
- Pages with no text are preserved rather than silently discarded.

`UnsupportedFile` represents a supported format that could not be processed. `UnsupportedUploadType` represents a file extension for which no loader is registered.

The golden fixture generator in `scripts/generate_chunker_goldens.py` uses the same native loaders as the application. When loader behavior intentionally changes, regenerate and review the affected golden fixtures.


### Add a new file type

Document loaders are registered in `src/ingestion/loaders/`. The same registry is used by upload validation and document processing.

To add a format:

1. Create a loader class implementing `DocumentLoader` from `src/ingestion/loaders/base.py`.
2. Declare its supported `extensions` and `mime_types`.
3. Implement `load(path)` and return `LoadedDocument` instances.
4. Register the loader in `create_default_loader_registry()` in `src/ingestion/loaders/__init__.py`.
5. Add the MIME type to `FILE_ALLOWED_EXTENTIONS` in the environment examples and update the configuration documentation.
6. Add loader, registry, upload-validation, and processing tests.

The registry is created once during application startup and shared by upload validation and the `ProcessAsset` use case. Do not create a global registry at module import time.

### Add a chunking strategy

Chunkers implement the `Chunker` protocol in `src/ingestion/chunkers/base.py`. A chunker accepts
loaded documents, `chunk_size`, and `chunk_overlap`, and returns ordered `Chunk` objects containing
text and metadata.

1. Implement the protocol in `src/ingestion/chunkers/`.
2. Register the strategy name in `create_default_chunker_factory()` in `src/ingestion/chunkers/__init__.py`.
3. Add tests for chunk boundaries, ordering, metadata, and overlap behavior.
4. Document the strategy name and behavior in the API reference.

The built-in factory currently registers only the newline-based `default` strategy. Its `chunk_overlap` argument is accepted but not applied.

## Testing

Run the test suite with:

\`\`\`bash
uv run pytest tests/ --cov=src --cov-report=term-missing
uvx ruff check tests/
\`\`\`

The test suite includes application use-case unit tests, infrastructure adapter tests, API workflow tests, and provider tests.

- Application use-case tests use fake implementations of the required ports. `ProcessAsset` tests cover successful processing, missing files, empty documents, empty chunks, unsupported loaders, loader failures, and persistence failures.
- Asset file resolver tests cover stored path resolution and invalid or unsafe paths.
- Asset processing repository integration tests verify chunk persistence and transactional asset status updates against PostgreSQL.
- API workflow and provider tests use fakes or mocked SDK clients and do not require API keys or external network calls.
- The pgvector integration tests use a real PostgreSQL database with the pgvector extension. They are skipped locally unless `PGVECTOR_TEST_DATABASE_URL` is set.
- CI starts a PostgreSQL pgvector service for integration testing.

The integration test fixture creates its database schema using SQLAlchemy metadata. It does not test Alembic migrations.

## Code style

Ruff is used in CI for the test suite. Until source-wide linting is enabled, match the style of the surrounding code, and keep these conventions:

- Routes stay thin. Application operations such as file ingestion and asset processing belong in use cases. The existing NLP workflow remains in `NLPController`.
- Application use cases depend on ports, not infrastructure implementations.
- Infrastructure adapters implement application ports and contain database and filesystem-specific operations.
- Provider-specific code stays inside `stores/`. Controllers talk to interfaces only.
- Async I/O methods on stores, repositories, and storage adapters must be awaited. Synchronous document loading and chunking in `ProcessAsset` run through `asyncio.to_thread`.
- Return a clear `signal` for every failure path in a route, and log the underlying error.

Expanding Ruff coverage to application source requires resolving the existing lint findings there.

## Commits and pull requests

Use conventional commits:

```text
type(scope): short summary
```

Types in use: `feat`, `fix`, `refactor`, `docs`, `chore`. Keep unrelated changes in separate commits, and add a line to `Changelog.md` under *Unreleased* for anything user-visible.

## Releasing

1. Move the *Unreleased* entries in `Changelog.md` under a new version heading with the date.
2. Update the version in `pyproject.toml` and `APP_VERSION` in your example env files.
3. Commit, then tag: `git tag vX.Y.Z && git push --tags`.
4. Publish a GitHub release with the changelog section as the notes.

Versioning follows [Semantic Versioning](https://semver.org). The older tags in the repository (`minirag-mongodv-v1`, `minirag26-mongodb-v1`, `minirag26-postgresql-pgvector-v2`) are course checkpoints, not releases.
