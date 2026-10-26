from __future__ import annotations

import argparse
import os
from collections.abc import Iterable

from sqlalchemy import MetaData, Table, create_engine, func, inspect, select, text
from sqlalchemy.engine import URL, make_url


def dependency_order(
    inspector, table_names: Iterable[str]
) -> list[str]:
    remaining = set(table_names)
    dependencies = {
        table: {
            foreign_key["referred_table"]
            for foreign_key in inspector.get_foreign_keys(table)
            if foreign_key["referred_table"] in remaining
            and foreign_key["referred_table"] != table
        }
        for table in remaining
    }
    ordered: list[str] = []

    while dependencies:
        ready = sorted(
            table for table, parents in dependencies.items() if not parents
        )
        if not ready:
            cycle = ", ".join(sorted(dependencies))
            raise RuntimeError(
                f"Cannot safely order tables with circular foreign keys: {cycle}"
            )
        ordered.extend(ready)
        for table in ready:
            del dependencies[table]
        for parents in dependencies.values():
            parents.difference_update(ready)

    return ordered


def migrate(source_path: str, target_url: URL, apply_changes: bool) -> None:
    if target_url.get_backend_name() != "postgresql":
        raise ValueError("TARGET_DATABASE_URL must point to PostgreSQL.")
    if target_url.drivername in {"postgresql", "postgresql+psycopg2"}:
        target_url = target_url.set(drivername="postgresql+psycopg")

    source_url = URL.create("sqlite", database=source_path)
    source_engine = create_engine(source_url)
    target_engine = create_engine(target_url)

    try:
        source_inspector = inspect(source_engine)
        source_tables = sorted(
            set(source_inspector.get_table_names()) - {"alembic_version"}
        )
        target_tables = set(inspect(target_engine).get_table_names())
        missing_tables = set(source_tables) - target_tables
        if missing_tables:
            raise RuntimeError(
                "The Render database is missing tables: "
                + ", ".join(sorted(missing_tables))
                + ". Apply the latest Alembic migrations first."
            )

        ordered_tables = dependency_order(source_inspector, source_tables)
        source_metadata = MetaData()
        target_metadata = MetaData()
        source_metadata.reflect(bind=source_engine, only=source_tables)
        target_metadata.reflect(bind=target_engine, only=source_tables)

        source_counts: dict[str, int] = {}
        target_counts: dict[str, int] = {}
        for name in ordered_tables:
            source_table = source_metadata.tables[name]
            target_table = target_metadata.tables[name]
            with source_engine.connect() as source_connection:
                source_count = source_connection.scalar(
                    select(func.count()).select_from(source_table)
                )
            source_counts[name] = source_count

            with target_engine.connect() as target_connection:
                target_count = target_connection.scalar(
                    select(func.count()).select_from(target_table)
                )
            target_counts[name] = target_count

        tables_to_copy = [
            name for name in ordered_tables if source_counts[name] > 0
        ]
        occupied_tables = [
            name for name in tables_to_copy if target_counts[name] > 0
        ]
        print("Source SQLite records:")
        for name in ordered_tables:
            if source_counts[name]:
                print(f"  {name}: {source_counts[name]}")
        print("Render tables with existing records:")
        for name in ordered_tables:
            if target_counts[name]:
                print(f"  {name}: {target_counts[name]}")

        if occupied_tables:
            raise RuntimeError(
                "Migration stopped without changing data because these Render "
                "tables already contain records: "
                + ", ".join(occupied_tables)
                + ". Do not clear them; resolve the existing records before retrying."
            )

        if not apply_changes:
            print("Dry run only. No records were written. Add --apply to migrate.")
            return

        with source_engine.connect() as source_connection:
            with target_engine.begin() as target_connection:
                for name in ordered_tables:
                    if not source_counts[name]:
                        continue
                    source_table = source_metadata.tables[name]
                    target_table = target_metadata.tables[name]
                    target_columns = set(target_table.c.keys())
                    source_rows = source_connection.execute(
                        select(source_table)
                    ).mappings()
                    rows = [
                        {
                            key: value
                            for key, value in row.items()
                            if key in target_columns
                        }
                        for row in source_rows
                    ]

                    for column in target_table.columns:
                        if (
                            column.name not in source_table.c
                            and not column.nullable
                            and column.default is None
                            and column.server_default is None
                            and column.identity is None
                            and column.computed is None
                        ):
                            raise RuntimeError(
                                f"Cannot copy {name}: required Render column "
                                f"{column.name} has no source value or default."
                            )

                    target_connection.execute(target_table.insert(), rows)

                for name in tables_to_copy:
                    target_table = target_metadata.tables[name]
                    for column in target_table.primary_key.columns:
                        try:
                            python_type = column.type.python_type
                        except (AttributeError, NotImplementedError):
                            continue
                        if python_type is not int:
                            continue
                        sequence_name = target_connection.scalar(
                            text(
                                "SELECT pg_get_serial_sequence(:table_name, "
                                ":column_name)"
                            ),
                            {
                                "table_name": name,
                                "column_name": column.name,
                            },
                        )
                        if sequence_name is None:
                            continue
                        maximum = target_connection.scalar(
                            select(func.max(column))
                        )
                        if maximum is not None:
                            target_connection.execute(
                                text(
                                    "SELECT setval(CAST(:sequence_name AS regclass), "
                                    ":value, true)"
                                ),
                                {
                                    "sequence_name": sequence_name,
                                    "value": maximum,
                                },
                            )

        print("Migration completed successfully.")
        for name in tables_to_copy:
            print(f"  {name}: copied {source_counts[name]} records")
    finally:
        source_engine.dispose()
        target_engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Copy records from the local TripOS SQLite database to an empty "
            "Render PostgreSQL database."
        )
    )
    parser.add_argument(
        "--source",
        default="tripos_dev.db",
        help="Path to the SQLite database (default: tripos_dev.db).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write records. Without this flag, the command only performs a dry run.",
    )
    args = parser.parse_args()

    raw_target_url = os.environ.get("TARGET_DATABASE_URL")
    if not raw_target_url:
        parser.error(
            "Set TARGET_DATABASE_URL to Render's External Database URL first."
        )
    migrate(args.source, make_url(raw_target_url), args.apply)


if __name__ == "__main__":
    main()
