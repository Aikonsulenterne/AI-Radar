from app.ingestion.normalize import extract_text, normalize_whitespace


def test_normalize_whitespace_collapses_without_changing_meaning() -> None:
    raw = "Linje  1\t\tmed   mellemrum\n\n\n\nLinje 2  \n"
    assert normalize_whitespace(raw) == "Linje 1 med mellemrum\n\nLinje 2"


def test_extract_text_plain() -> None:
    result = extract_text("text/plain; charset=utf-8", b"Hej   verden\n")
    assert result.text == "Hej verden"
    assert result.title is None


def test_extract_text_html_skips_script_and_reads_title() -> None:
    html = (
        "<html><head><title>Test  titel</title><script>evil()</script></head>"
        "<body><p>Første afsnit</p><style>p{}</style><p>Andet afsnit</p></body></html>"
    )
    result = extract_text("text/html", html.encode())
    assert result.title == "Test titel"
    assert result.text is not None
    assert "Første afsnit" in result.text
    assert "Andet afsnit" in result.text
    assert "evil" not in result.text


def test_extract_text_unknown_mime_returns_none_not_a_guess() -> None:
    result = extract_text("application/zip", b"PK\x03\x04")
    assert result.text is None
    assert result.title is None
