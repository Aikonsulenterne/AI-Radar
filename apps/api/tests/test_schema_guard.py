"""Opstartssikringen må kun gentage, hvad migrationen allerede gør."""

from pathlib import Path

from app.schema_guard import VENDOR_MIGRATION_STATEMENTS

MIGRATION = (
    Path(__file__).resolve().parents[3]
    / "supabase"
    / "migrations"
    / "20261008090000_vendor_offerings.sql"
)


def test_every_guard_statement_is_in_the_migration() -> None:
    migration = " ".join(MIGRATION.read_text().split()).lower()
    for statement in VENDOR_MIGRATION_STATEMENTS:
        assert " ".join(statement.split()).lower() in migration, statement


def test_guard_is_a_no_op_on_sqlite() -> None:
    from app.schema_guard import ensure_vendor_schema

    ensure_vendor_schema()  # SQLite i testene: ingen fejl, ingen ændringer


def test_source_pack_matches_the_ops_script() -> None:
    import re

    from app.schema_guard import SOURCE_PACK

    script = (MIGRATION.parents[1] / "ops" / "kundecenter_sources.sql").read_text()
    urls = re.findall(r"'(https://[^']+)', (?:null|'[A-Z]+')\)", script)
    assert urls == [row[3] for row in SOURCE_PACK]
