
from logging.config import fileConfig

from alembic import context
from schemas import SQLAlchemyBase
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import URL

from helpers import get_database_settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLAlchemyBase.metadata


def get_database_url() -> URL:
    settings = get_database_settings()

    return URL.create(
        drivername="postgresql+psycopg2",
        username=settings.POSTGRES_USERNAME,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_MAIN_DATABASE,
    )


def run_migrations_offline() -> None:
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        {
            **config.get_section(config.config_ini_section, {}),
            "sqlalchemy.url": get_database_url().render_as_string(
                hide_password=False
            ),
        },
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
