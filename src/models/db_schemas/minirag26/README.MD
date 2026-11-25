# Alembic migrations

Run these commands from this directory unless stated otherwise.

## Configure the database connection

Create the local Alembic config file:

```bash
cp alembic.ini.example alembic.ini
```

The INI file configures Alembic's migration script location and logging. Do **not** put database credentials in `sqlalchemy.url`: `alembic/env.py` builds the connection URL from the shared `DatabaseSettings`.

Set these variables in `src/.env.app` (or in the process environment):

- `POSTGRES_USERNAME`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `POSTGRES_MAIN_DATABASE`

The same settings are used by the application and Alembic. Environment variables override values loaded from `src/.env.app`.

## Apply migrations

```bash
uv run alembic upgrade head
```

## Create a migration

After changing SQLAlchemy models:

```bash
uv run alembic revision --autogenerate -m "Add ..."
```

Review the generated migration before applying it. Autogenerate does not replace manual review, especially for data migrations, constraint validation, concurrent indexes, or destructive operations.

## Docker

The Docker image copies the tracked `docker/minirag/alembic.example.ini` into the image as its Alembic config. At container startup, `entrypoint.sh` runs `alembic upgrade head`; the database connection comes from the FastAPI container's environment variables.
