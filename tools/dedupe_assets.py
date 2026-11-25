import argparse
import sys
from collections import defaultdict
from pathlib import Path

from sqlalchemy import URL, create_engine, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "models" / "db_schemas" / "minirag26"))

from helpers import get_database_settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deduplicate assets by project and asset name."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the deduplication. Without this flag, only preview changes.",
    )
    args = parser.parse_args()

    settings = get_database_settings()
    database = settings.POSTGRES_MAIN_DATABASE

    print(f"Target database: {database}")
    print(f"Mode: {'APPLY' if args.apply else 'DRY RUN'}")

    if args.apply:
        confirmation = input(
            f"Type the database name '{database}' to confirm: "
        ).strip()
        if confirmation != database:
            print("Confirmation did not match. No changes made.")
            return 1

    url = URL.create(
        "postgresql+psycopg2",
        username=settings.POSTGRES_USERNAME,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=database,
    )
    engine = create_engine(url)

    try:
        with engine.begin() as conn:
            conn.execute(
                text("LOCK TABLE assets, chunks IN SHARE ROW EXCLUSIVE MODE")
            )

            rows = conn.execute(
                text("""
                    SELECT asset_id, asset_project_id, asset_name
                    FROM assets
                    ORDER BY
                        asset_project_id,
                        asset_name,
                        asset_pushed_at DESC,
                        asset_id DESC
                    FOR UPDATE
                """)
            ).mappings().all()

            groups = defaultdict(list)
            for row in rows:
                groups[(row["asset_project_id"], row["asset_name"])].append(
                    row["asset_id"]
                )

            duplicates = {
                key: asset_ids
                for key, asset_ids in groups.items()
                if len(asset_ids) > 1
            }

            invalid_statuses = conn.execute(
                text("""
                    SELECT asset_status, COUNT(*) AS row_count,
                           ARRAY_AGG(asset_id ORDER BY asset_id) AS asset_ids
                    FROM assets
                    WHERE asset_status NOT IN (0, 1, 2)
                       OR asset_status IS NULL
                    GROUP BY asset_status
                    ORDER BY asset_status
                """)
            ).mappings().all()

            if not duplicates:
                print("No duplicate asset names found.")
            else:
                print(f"Duplicate groups found: {len(duplicates)}")

            total_repointed = 0
            total_deleted = 0

            for (project_id, asset_name), asset_ids in duplicates.items():
                keeper_id = asset_ids[0]
                duplicate_ids = asset_ids[1:]

                print(
                    f"\nProject {project_id}, name={asset_name!r}:"
                    f"\n  Keep asset_id={keeper_id}"
                    f"\n  Remove asset_ids={duplicate_ids}"
                )

                for duplicate_id in duplicate_ids:
                    chunk_count = conn.execute(
                        text("""
                            SELECT COUNT(*)
                            FROM chunks
                            WHERE chunk_asset_id = :asset_id
                        """),
                        {"asset_id": duplicate_id},
                    ).scalar_one()

                    print(
                        f"  asset_id={duplicate_id}: "
                        f"{chunk_count} chunk(s) will be re-pointed"
                    )

                    if args.apply:
                        updated = conn.execute(
                            text("""
                                UPDATE chunks
                                SET chunk_asset_id = :keeper_id
                                WHERE chunk_asset_id = :duplicate_id
                            """),
                            {
                                "keeper_id": keeper_id,
                                "duplicate_id": duplicate_id,
                            },
                        )
                        deleted = conn.execute(
                            text("""
                                DELETE FROM assets
                                WHERE asset_id = :duplicate_id
                            """),
                            {"duplicate_id": duplicate_id},
                        )

                        total_repointed += updated.rowcount
                        total_deleted += deleted.rowcount

            if invalid_statuses:
                print("\nWARNING: Invalid statuses remain; this script does not fix them.")
                for item in invalid_statuses:
                    print(
                        f"  status={item['asset_status']!r}, "
                        f"count={item['row_count']}, "
                        f"asset_ids={item['asset_ids']}"
                    )

            if args.apply:
                print("\nChanges applied:")
                print(f"  Chunks re-pointed: {total_repointed}")
                print(f"  Duplicate assets deleted: {total_deleted}")
            else:
                print("\nDry run only. No rows were changed.")

    finally:
        engine.dispose()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
