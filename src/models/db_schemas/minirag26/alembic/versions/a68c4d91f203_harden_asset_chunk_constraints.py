
"""Harden asset and chunk relational constraints.

Revision ID: a68c4d91f203
Revises: 4f840028cedb
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a68c4d91f203"
down_revision: Union[str, Sequence[str], None] = "4f840028cedb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UNIQUE_INDEX = "uq_assets_project_asset_name"
COMPOSITE_INDEX = "ix_chunks_project_asset"
OLD_PROJECT_INDEX = "ix_chunk_project_id"


def _preflight() -> None:
    """Abort before schema changes if existing data violates new constraints."""
    bind = op.get_bind()

    duplicates = bind.execute(
        sa.text(
            """
            SELECT
                asset_project_id,
                asset_name,
                COUNT(*) AS duplicate_count,
                ARRAY_AGG(
                    asset_id
                    ORDER BY asset_pushed_at DESC, asset_id DESC
                ) AS asset_ids
            FROM assets
            GROUP BY asset_project_id, asset_name
            HAVING COUNT(*) > 1
            ORDER BY asset_project_id, asset_name
            """
        )
    ).mappings().all()

    invalid_statuses = bind.execute(
        sa.text(
            """
            SELECT
                asset_status,
                COUNT(*) AS row_count,
                ARRAY_AGG(asset_id ORDER BY asset_id) AS asset_ids
            FROM assets
            WHERE asset_status NOT IN (0, 1, 2)
               OR asset_status IS NULL
            GROUP BY asset_status
            ORDER BY asset_status
            """
        )
    ).mappings().all()

    problems = []

    if duplicates:
        problems.append("Duplicate asset names within projects:")
        for row in duplicates:
            problems.append(
                f"  project_id={row['asset_project_id']}, "
                f"asset_name={row['asset_name']!r}, "
                f"count={row['duplicate_count']}, "
                f"asset_ids={row['asset_ids']}"
            )

    if invalid_statuses:
        problems.append("Invalid asset statuses:")
        for row in invalid_statuses:
            problems.append(
                f"  asset_status={row['asset_status']!r}, "
                f"count={row['row_count']}, "
                f"asset_ids={row['asset_ids']}"
            )

    if problems:
        raise RuntimeError(
            "Migration pre-flight failed. Resolve these data violations "
            "before upgrading:\n" + "\n".join(problems)
        )


def _ensure_concurrent_index(name: str, create_sql: str) -> None:
    """Create a concurrent index, recovering from an invalid leftover index."""
    bind = op.get_bind()

    existing = bind.execute(
        sa.text(
            """
            SELECT index_class.relname, index_data.indisvalid
            FROM pg_class AS index_class
            JOIN pg_namespace AS namespace
              ON namespace.oid = index_class.relnamespace
            JOIN pg_index AS index_data
              ON index_data.indexrelid = index_class.oid
            WHERE namespace.nspname = current_schema()
              AND index_class.relname = :index_name
            """
        ),
        {"index_name": name},
    ).mappings().first()

    if existing and existing["indisvalid"]:
        return

    if existing:
        with op.get_context().autocommit_block():
            op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")

    with op.get_context().autocommit_block():
        op.execute(create_sql)


def _drop_concurrent_index(name: str) -> None:
    with op.get_context().autocommit_block():
        op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {name}")


def upgrade() -> None:
    _preflight()

    # Concurrent index creation must happen before transactional DDL.
    # If a later operation fails, these indexes can safely be reused
    # when the migration is retried.
    _ensure_concurrent_index(
        UNIQUE_INDEX,
        """
        CREATE UNIQUE INDEX CONCURRENTLY uq_assets_project_asset_name
        ON assets (asset_project_id, asset_name)
        """,
    )

    _ensure_concurrent_index(
        COMPOSITE_INDEX,
        """
        CREATE INDEX CONCURRENTLY ix_chunks_project_asset
        ON chunks (chunk_project_id, chunk_asset_id)
        """,
    )

    # All remaining operations are transactional.
    op.execute(
        """
        ALTER TABLE assets
        ADD CONSTRAINT uq_assets_project_asset_name
        UNIQUE USING INDEX uq_assets_project_asset_name
        """
    )

    op.execute(
        """
        ALTER TABLE assets
        ADD CONSTRAINT ck_assets_asset_status
        CHECK (asset_status IN (0, 1, 2))
        NOT VALID
        """
    )
    op.execute(
        """
        ALTER TABLE assets
        VALIDATE CONSTRAINT ck_assets_asset_status
        """
    )

    op.drop_constraint(
        "assets_asset_project_id_fkey",
        "assets",
        type_="foreignkey",
    )
    op.execute(
        """
        ALTER TABLE assets
        ADD CONSTRAINT assets_asset_project_id_fkey
        FOREIGN KEY (asset_project_id)
        REFERENCES projects (project_id)
        ON DELETE CASCADE
        NOT VALID
        """
    )
    op.execute(
        """
        ALTER TABLE assets
        VALIDATE CONSTRAINT assets_asset_project_id_fkey
        """
    )

    op.drop_constraint(
        "chunks_chunk_asset_id_fkey",
        "chunks",
        type_="foreignkey",
    )
    op.execute(
        """
        ALTER TABLE chunks
        ADD CONSTRAINT chunks_chunk_asset_id_fkey
        FOREIGN KEY (chunk_asset_id)
        REFERENCES assets (asset_id)
        ON DELETE CASCADE
        NOT VALID
        """
    )
    op.execute(
        """
        ALTER TABLE chunks
        VALIDATE CONSTRAINT chunks_chunk_asset_id_fkey
        """
    )

    op.drop_constraint(
        "chunks_chunk_project_id_fkey",
        "chunks",
        type_="foreignkey",
    )
    op.execute(
        """
        ALTER TABLE chunks
        ADD CONSTRAINT chunks_chunk_project_id_fkey
        FOREIGN KEY (chunk_project_id)
        REFERENCES projects (project_id)
        ON DELETE CASCADE
        NOT VALID
        """
    )
    op.execute(
        """
        ALTER TABLE chunks
        VALIDATE CONSTRAINT chunks_chunk_project_id_fkey
        """
    )

    # The replacement index already exists, so the old index can be
    # dropped transactionally.
    op.drop_index(OLD_PROJECT_INDEX, table_name="chunks")


def downgrade() -> None:
    # Create the old index concurrently before transactional changes.
    _ensure_concurrent_index(
        OLD_PROJECT_INDEX,
        """
        CREATE INDEX CONCURRENTLY ix_chunk_project_id
        ON chunks (chunk_project_id)
        """,
    )

    # Restore the original non-cascading foreign keys.
    op.drop_constraint(
        "chunks_chunk_project_id_fkey",
        "chunks",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "chunks_chunk_project_id_fkey",
        "chunks",
        "projects",
        ["chunk_project_id"],
        ["project_id"],
    )

    op.drop_constraint(
        "chunks_chunk_asset_id_fkey",
        "chunks",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "chunks_chunk_asset_id_fkey",
        "chunks",
        "assets",
        ["chunk_asset_id"],
        ["asset_id"],
    )

    op.drop_constraint(
        "assets_asset_project_id_fkey",
        "assets",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "assets_asset_project_id_fkey",
        "assets",
        "projects",
        ["asset_project_id"],
        ["project_id"],
    )

    op.drop_constraint(
        "ck_assets_asset_status",
        "assets",
        type_="check",
    )

    op.drop_constraint(
        UNIQUE_INDEX,
        "assets",
        type_="unique",
    )

    op.drop_index(COMPOSITE_INDEX, table_name="chunks")
