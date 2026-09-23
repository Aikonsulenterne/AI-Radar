"""ORM-modellerne skal passe til skemaet fra supabase/migrations.

Migrations ejer DDL'en, men SQLite-testene bygger deres skema af modellerne
selv — så en kolonne, der findes i modellen men mangler i en migration, går
ubemærket igennem dér og fejler først i staging. Denne test kører kun mod
PostgreSQL (TEST_DATABASE_URL) og sammenligner hver tabel og kolonne.
"""

import pytest
from sqlalchemy import create_engine, inspect

import app.main  # noqa: F401  (registrerer alle modeller på Base)
from app.db import Base
from tests.conftest import TEST_DATABASE_URL

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="Kræver PostgreSQL med migrations (TEST_DATABASE_URL)."
)


def test_every_orm_column_exists_in_the_migrated_schema() -> None:
    assert TEST_DATABASE_URL is not None
    engine = create_engine(TEST_DATABASE_URL)
    inspector = inspect(engine)
    migrated_tables = set(inspector.get_table_names(schema="public"))

    problems: list[str] = []
    for table in Base.metadata.sorted_tables:
        if table.name not in migrated_tables:
            problems.append(f"{table.name}: tabellen findes ikke i migrations")
            continue
        migrated = {column["name"]: column for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name not in migrated:
                problems.append(f"{table.name}.{column.name}: kolonnen mangler i migrations")
                continue
            if bool(column.nullable) != bool(migrated[column.name]["nullable"]):
                problems.append(
                    f"{table.name}.{column.name}: nullable er {column.nullable} i modellen, "
                    f"{migrated[column.name]['nullable']} i migrations"
                )
    engine.dispose()

    assert not problems, "Skemadrift mellem ORM og migrations:\n" + "\n".join(problems)
