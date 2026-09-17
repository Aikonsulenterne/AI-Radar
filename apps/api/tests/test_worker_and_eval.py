"""Worker-kørsel og evalueringsrunner (Slice 6)."""

import json
from pathlib import Path

from app.evaluation import EvalRecord, evaluate, load_dataset
from tests.conftest import EXTRACTION_RESPONSE, FakeProvider


def test_eval_report_metrics_with_fake_provider() -> None:
    provider = FakeProvider()
    records = [
        EvalRecord(
            text=(
                "Danske Bank bruger Agent Assist i kundeservice. "
                "Banken rapporterer 20 procent lavere efterbehandlingstid."
            ),
            relevant=True,
            expected_claims=[
                {"subject_name": "Danske Bank", "predicate": "USES_CAPABILITY"},
                {"subject_name": "Danske Bank", "predicate": "REPORTED_EFFECT"},
            ],
        ),
    ]
    report = evaluate(provider, records)
    summary = report.summary()
    assert summary["records"] == 1
    assert summary["relevance_precision"] == 1.0
    assert summary["claim_recall"] == 1.0
    # Fixture-svaret indeholder ét uddrag, der ikke findes ordret i teksten.
    expected_excerpts = len(EXTRACTION_RESPONSE["claims"])
    assert report.excerpts_total == expected_excerpts
    assert report.excerpts_verbatim == expected_excerpts - 1


def test_load_dataset_parses_jsonl(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset.jsonl"
    dataset.write_text(
        json.dumps({"text": "abc", "relevant": False, "expected_claims": []}) + "\n\n"
    )
    records = load_dataset(dataset)
    assert len(records) == 1
    assert records[0].relevant is False
