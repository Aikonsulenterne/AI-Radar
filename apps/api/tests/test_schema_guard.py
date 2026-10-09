"""Opstartssikringen må kun gentage, hvad migrationen allerede gør."""

from pathlib import Path

from fastapi.testclient import TestClient

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


def test_health_reports_schema_status_only_when_asked(client: TestClient) -> None:
    plain = client.get("/api/v1/health").json()
    assert plain["status"] == "ok"
    assert plain["schema_status"] == "ikke tjekket"
    checked = client.get("/api/v1/health?schema=true").json()
    assert checked["status"] == "ok"
    assert checked["schema_status"] == "ikke tjekket"  # SQLite i testene


def test_unexpected_error_is_json_with_cors_header() -> None:
    from app.config import get_settings
    from app.main import app

    def boom() -> None:
        raise RuntimeError("intern detalje")

    app.add_api_route("/api/v1/_test_boom", boom)
    try:
        origin = get_settings().cors_origin_list[0]
        with TestClient(app, raise_server_exceptions=False) as raw:
            response = raw.get("/api/v1/_test_boom", headers={"Origin": origin})
    finally:
        app.router.routes = [
            r for r in app.router.routes if getattr(r, "path", "") != "/api/v1/_test_boom"
        ]
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "server_error"
    assert "intern detalje" not in response.text
    assert response.headers["access-control-allow-origin"] == origin
