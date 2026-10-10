# Development guide

How the code is organized, how to run it while you work on it, and the recipes for the most common changes. For first-time setup, follow the README's [local development](../README.md#local-development-uv) section.

## Project layout

```text
src/
├── main.py            # App creation and startup/shutdown (lifespan)
├── routes/            # HTTP endpoints: base, data, nlp
├── controllers/       # Business logic
├── models/
│   ├── schemas/       # Pydantic request/response models
│   ├── enums/         # Response signals, provider names, asset types
│   ├── db_schemas/    # SQLAlchemy tables and Alembic migrations
│   └── *DataModel.py  # Database access for projects, assets, chunks
├── stores/
│   ├── llm/           # LLM interface, factory, providers, prompt templates
│   └── vectordb/      # Vector store interface, factory, providers
├── helpers/config.py  # Settings
└── utils/metrics.py   # Prometheus middleware
docker/                # Compose stack, Dockerfile, Nginx, Prometheus, env examples
docs/                  # This documentation
```

### How a request flows

```text
route  ->  controller  ->  data model (PostgreSQL)
                      ->  LLM client / vector store client  (created once at startup)
```

- **Routes** validate input, call controllers, and build the JSON response with a `signal`.
- **Controllers** hold the logic. `ProcessController` loads and chunks files, `NLPController` indexes, searches, and answers, and `DataController` validates uploads.
- **Clients** (`app.generation_client`, `app.embedding_client`, `app.vectordb_client`, `app.db_client`) are created in the lifespan function in `main.py` and read by routes through `request.app`.

The architecture diagrams are in the README.

## Running locally

```bash
uv sync
cp src/.env.example src/.env.app          # then edit it
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
5. Update [API reference](api.md) and regenerate `docs/openapi.json` (the command is at the bottom of that file).

Signal strings are part of the public API. Changing an existing one is a breaking change and belongs in the changelog.

### Add a setting

Follow the steps in [Configuration](configuration.md#adding-a-new-setting).

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

See [Adding a provider](adding-a-provider.md).

### Add a new file type (planned work)

Loading happens in `ProcessController._get_file_loader`, which maps a file extension to a loader. A new type needs:

1. The extension in `ProcessingEnum`.
2. The MIME type in `FILE_ALLOWED_EXTENTIONS`.
3. A branch in `_get_file_loader` returning a loader whose `load()` yields objects with `page_content` and `metadata`.
4. Documentation updates (README features, [Configuration](configuration.md), changelog).

## Testing

There is no automated test suite yet, and adding one is on the roadmap. Until then, verify changes by running the full flow from the README against a small document: upload, process, push, search, answer. For changes to a provider, run that flow with the provider selected.

A good starting setup for contributors is `pytest` with `httpx`'s async client against the FastAPI app, and the provider interfaces replaced by small fakes so tests need neither a database nor API keys.

## Code style

No formatter or linter is enforced yet. Until one is added, match the style of the surrounding code, and keep these conventions:

- Routes stay thin. Logic belongs in controllers.
- Provider-specific code stays inside `stores/`. Controllers talk to interfaces only.
- I/O methods on stores and data models are `async`, so always `await` them.
- Return a clear `signal` for every failure path in a route, and log the underlying error.

Adding `ruff` and a pre-commit configuration would be a welcome contribution.

## Commits and pull requests

Use conventional commits:

```text
type(scope): short summary
```

Types in use: `feat`, `fix`, `refactor`, `docs`, `chore`. Keep unrelated changes in separate commits, and add a line to `CHANGELOG.md` under *Unreleased* for anything user-visible.

## Releasing

1. Move the *Unreleased* entries in `CHANGELOG.md` under a new version heading with the date.
2. Update the version in `pyproject.toml` and `APP_VERSION` in your example env files.
3. Commit, then tag: `git tag vX.Y.Z && git push --tags`.
4. Publish a GitHub release with the changelog section as the notes.

Versioning follows [Semantic Versioning](https://semver.org). The older tags in the repository (`minirag-mongodv-v1`, `minirag26-mongodb-v1`, `minirag26-postgresql-pgvector-v2`) are course checkpoints, not releases.
