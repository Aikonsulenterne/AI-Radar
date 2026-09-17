from app.pipeline.entities import normalize_alias, slugify


def test_normalize_alias_collapses_case_and_whitespace() -> None:
    assert normalize_alias("  Danske   BANK ") == "danske bank"


def test_slugify_produces_url_safe_slug() -> None:
    assert slugify("Danske Bank A/S") == "danske-bank-a-s"
    assert slugify("!!!") == "entity"
