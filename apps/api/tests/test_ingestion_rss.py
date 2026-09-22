"""RSS-hentning: feedparsing, artikelhentning og afvisning af utrygge links."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.errors import ApiError
from app.ingestion.feed import parse_feed
from app.ingestion.fetch import FetchResult

RSS_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Eksempelkilde</title>
    <item>
      <title>Bank tager Agent Assist i brug</title>
      <link>https://example.org/artikel-1</link>
      <pubDate>Tue, 15 Sep 2026 08:00:00 +0000</pubDate>
    </item>
    <item>
      <title>Forsyningsselskab automatiserer fakturaflow</title>
      <link>https://example.org/artikel-2</link>
    </item>
  </channel>
</rss>
"""

ATOM_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Eksempelkilde</title>
  <entry>
    <title>Energiselskab tester prognosemodel</title>
    <link rel="alternate" href="https://example.org/atom-1"/>
    <published>2026-09-15T08:00:00Z</published>
  </entry>
</feed>
"""


def _create_rss_source(client: TestClient, headers: dict[str, str], **overrides: Any) -> str:
    body: dict[str, Any] = {
        "name": "Feedkilde",
        "source_type": "media",
        "retrieval_method": "rss",
        "access_class": "public",
        "endpoint_url": "https://example.org/feed.xml",
    }
    body.update(overrides)
    response = client.post("/api/v1/sources", json=body, headers=headers)
    assert response.status_code == 201, response.text
    source_id: str = response.json()["id"]
    return source_id


def _article(title: str) -> bytes:
    return f"<html><head><title>{title}</title></head><body><p>{title}</p></body></html>".encode()


def test_parse_feed_reads_rss_items() -> None:
    entries = parse_feed(RSS_FEED)
    assert [entry.link for entry in entries] == [
        "https://example.org/artikel-1",
        "https://example.org/artikel-2",
    ]
    assert entries[0].title == "Bank tager Agent Assist i brug"
    assert entries[0].published_at is not None
    # Uden pubDate gættes der ikke et tidspunkt.
    assert entries[1].published_at is None


def test_parse_feed_reads_atom_entries() -> None:
    entries = parse_feed(ATOM_FEED)
    assert len(entries) == 1
    assert entries[0].link == "https://example.org/atom-1"
    assert entries[0].title == "Energiselskab tester prognosemodel"


def test_parse_feed_rejects_dtd_and_unknown_formats() -> None:
    with pytest.raises(ApiError) as dtd:
        parse_feed(b'<?xml version="1.0"?><!DOCTYPE rss [<!ENTITY a "b">]><rss></rss>')
    assert dtd.value.code == "feed_invalid"

    with pytest.raises(ApiError) as other:
        parse_feed(b"<html><body>ikke et feed</body></html>")
    assert other.value.code == "feed_invalid"


def test_run_rss_ingests_each_entry_and_is_idempotent(
    client: TestClient, admin_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    source_id = _create_rss_source(client, admin_headers)

    def fake_fetch(url: str, timeout_seconds: float, max_bytes: int) -> FetchResult:
        if url.endswith("feed.xml"):
            return FetchResult(data=RSS_FEED, content_type="application/rss+xml", final_url=url)
        return FetchResult(data=_article(url), content_type="text/html", final_url=url)

    monkeypatch.setattr("app.ingestion.run.fetch_url", fake_fetch)

    first = client.post(f"/api/v1/sources/{source_id}/run", headers=admin_headers)
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["created_count"] == 2
    assert body["failures"] == []

    # Feedets titel vinder over dokumentets egen, og pubDate bliver til published_at.
    documents = {item["document"]["canonical_url"]: item["document"] for item in body["documents"]}
    article_one = documents["https://example.org/artikel-1"]
    assert article_one["title"] == "Bank tager Agent Assist i brug"
    assert article_one["published_at"] is not None
    assert documents["https://example.org/artikel-2"]["published_at"] is None

    second = client.post(f"/api/v1/sources/{source_id}/run", headers=admin_headers)
    assert second.json()["created_count"] == 0
    assert second.json()["unchanged_count"] == 2


def test_run_rss_collects_entry_failures_without_failing_the_run(
    client: TestClient, admin_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    source_id = _create_rss_source(client, admin_headers)
    feed = RSS_FEED.replace(b"https://example.org/artikel-2", b"http://127.0.0.1/intern")
    fetched_urls: list[str] = []

    def fake_fetch(url: str, timeout_seconds: float, max_bytes: int) -> FetchResult:
        fetched_urls.append(url)
        if url.endswith("feed.xml"):
            return FetchResult(data=feed, content_type="application/rss+xml", final_url=url)
        if url.endswith("artikel-1"):
            raise ApiError(502, "fetch_failed", "Kilden svarede med HTTP 404.")
        return FetchResult(data=_article(url), content_type="text/html", final_url=url)

    monkeypatch.setattr("app.ingestion.run.fetch_url", fake_fetch)

    response = client.post(f"/api/v1/sources/{source_id}/run", headers=admin_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["documents"] == []
    codes = {failure["code"] for failure in body["failures"]}
    assert codes == {"fetch_failed", "unsafe_url"}
    # Den interne adresse blev afvist før nogen HTTP-forespørgsel.
    assert "http://127.0.0.1/intern" not in fetched_urls


def test_run_rss_reports_invalid_feed(
    client: TestClient, admin_headers: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    source_id = _create_rss_source(client, admin_headers)

    def fake_fetch(url: str, timeout_seconds: float, max_bytes: int) -> FetchResult:
        return FetchResult(data=b"ikke xml", content_type="application/rss+xml", final_url=url)

    monkeypatch.setattr("app.ingestion.run.fetch_url", fake_fetch)

    response = client.post(f"/api/v1/sources/{source_id}/run", headers=admin_headers)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "feed_invalid"
