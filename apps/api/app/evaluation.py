"""Evaluering af AI-laget mod et manuelt vurderet reference-datasæt
(Technical Master §16).

Datasæt: JSONL, én record pr. linje:
{"text": "...", "relevant": true, "expected_claims": [
    {"subject_name": "...", "predicate": "USES_CAPABILITY"}]}

Kørsel: `uv run python -m app.evaluation --dataset ../../evaluation/dataset.jsonl`
(kræver konfigureret AI-provider). Metrikker: relevance precision/recall,
claim precision/recall på (subjekt, predicate) og excerpt correctness.
"""

import argparse
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, Field

from app.ai.prompts import (
    EXTRACTION_PROMPT_ID,
    EXTRACTION_PROMPT_VERSION,
    EXTRACTION_SYSTEM,
    RELEVANCE_PROMPT_ID,
    RELEVANCE_PROMPT_VERSION,
    RELEVANCE_SYSTEM,
)
from app.ai.provider import AIProvider, get_ai_provider
from app.ai.schemas import (
    AISchemaError,
    ExtractionResult,
    RelevanceResult,
    call_with_schema,
)

logger = logging.getLogger("ai_radar.evaluation")


class ExpectedClaim(BaseModel):
    subject_name: str
    predicate: str


class EvalRecord(BaseModel):
    text: str
    relevant: bool
    expected_claims: list[ExpectedClaim] = Field(default_factory=list)


@dataclass
class EvalReport:
    records: int = 0
    schema_failures: int = 0
    relevance_true_positive: int = 0
    relevance_false_positive: int = 0
    relevance_false_negative: int = 0
    claim_true_positive: int = 0
    claim_false_positive: int = 0
    claim_false_negative: int = 0
    excerpts_total: int = 0
    excerpts_verbatim: int = 0
    notes: list[str] = field(default_factory=list)

    @staticmethod
    def _ratio(numerator: int, denominator: int) -> float | None:
        return round(numerator / denominator, 3) if denominator else None

    def summary(self) -> dict[str, object]:
        return {
            "records": self.records,
            "schema_failures": self.schema_failures,
            "relevance_precision": self._ratio(
                self.relevance_true_positive,
                self.relevance_true_positive + self.relevance_false_positive,
            ),
            "relevance_recall": self._ratio(
                self.relevance_true_positive,
                self.relevance_true_positive + self.relevance_false_negative,
            ),
            "claim_precision": self._ratio(
                self.claim_true_positive,
                self.claim_true_positive + self.claim_false_positive,
            ),
            "claim_recall": self._ratio(
                self.claim_true_positive,
                self.claim_true_positive + self.claim_false_negative,
            ),
            "excerpt_correctness": self._ratio(self.excerpts_verbatim, self.excerpts_total),
        }


def load_dataset(path: Path) -> list[EvalRecord]:
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(EvalRecord.model_validate(json.loads(line)))
    return records


def evaluate(provider: AIProvider, records: list[EvalRecord]) -> EvalReport:
    report = EvalReport()
    for record in records:
        report.records += 1
        try:
            relevance = call_with_schema(
                provider,
                prompt_id=RELEVANCE_PROMPT_ID,
                prompt_version=RELEVANCE_PROMPT_VERSION,
                system=RELEVANCE_SYSTEM,
                user=record.text,
                result_model=RelevanceResult,
            )
        except AISchemaError:
            report.schema_failures += 1
            continue

        if relevance.relevant and record.relevant:
            report.relevance_true_positive += 1
        elif relevance.relevant and not record.relevant:
            report.relevance_false_positive += 1
        elif not relevance.relevant and record.relevant:
            report.relevance_false_negative += 1

        if not relevance.relevant:
            report.claim_false_negative += len(record.expected_claims)
            continue

        try:
            extraction = call_with_schema(
                provider,
                prompt_id=EXTRACTION_PROMPT_ID,
                prompt_version=EXTRACTION_PROMPT_VERSION,
                system=EXTRACTION_SYSTEM,
                user=record.text,
                result_model=ExtractionResult,
            )
        except AISchemaError:
            report.schema_failures += 1
            continue

        expected = {(c.subject_name.casefold(), c.predicate) for c in record.expected_claims}
        found = {(c.subject_name.casefold(), c.predicate.value) for c in extraction.claims}
        report.claim_true_positive += len(expected & found)
        report.claim_false_positive += len(found - expected)
        report.claim_false_negative += len(expected - found)

        for claim in extraction.claims:
            report.excerpts_total += 1
            if claim.supporting_excerpt in record.text:
                report.excerpts_verbatim += 1
    return report


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Evaluér AI-laget mod reference-datasæt")
    parser.add_argument("--dataset", required=True, type=Path)
    args = parser.parse_args()

    provider = get_ai_provider()
    if provider is None:
        raise SystemExit("AI-provider er ikke konfigureret (AI_PROVIDER_BASE_URL/AI_MODEL_ID).")

    records = load_dataset(args.dataset)
    report = evaluate(provider, records)
    print(json.dumps(report.summary(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
