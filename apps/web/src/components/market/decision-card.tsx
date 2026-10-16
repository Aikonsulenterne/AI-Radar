"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ApiClientError,
  answerDecision,
  type DecisionAnswer,
  type OkDecision,
} from "../../app/lib/api";
import { GainLine } from "./gain-line";

const ANSWERS: { value: DecisionAnswer; label: string }[] = [
  { value: "ja", label: "Ja" },
  { value: "nej", label: "Nej" },
  { value: "senere", label: "Senere" },
];

function shortDate(value: string): string {
  return new Intl.DateTimeFormat("da-DK", {
    day: "numeric",
    month: "short",
    timeZone: "Europe/Copenhagen",
  }).format(new Date(value));
}

/** Ét ja/nej-spørgsmål: hvad et ja kræver, hvad andre fik, første skridt.
 * Svaret gemmes med dato (kun beslutning og dato — ingen tal). */
export function DecisionCard({ decision }: { decision: OkDecision }) {
  const router = useRouter();
  const [answer, setAnswer] = useState(decision.answer);
  const [answeredAt, setAnsweredAt] = useState(decision.answered_at);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function choose(value: DecisionAnswer) {
    setBusy(true);
    setError(null);
    try {
      const saved = await answerDecision(decision.key, value);
      setAnswer(saved.answer);
      setAnsweredAt(saved.answered_at);
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Svaret blev ikke gemt. Prøv igen.");
    } finally {
      setBusy(false);
    }
  }

  const requires = [decision.owner, decision.duration].filter(Boolean).join(" · ");
  return (
    <li className="decision-card">
      <p className="decision-q">{decision.question}</p>
      <dl className="decision-meta">
        {requires ? (
          <div>
            <dt>Kræver</dt>
            <dd>{requires}</dd>
          </div>
        ) : null}
        <div>
          <dt>Andre</dt>
          <dd>
            <GainLine gain={decision.gain} prefix="Fik" />
          </dd>
        </div>
        {decision.first_step ? (
          <div>
            <dt>Første skridt</dt>
            <dd>{decision.first_step}</dd>
          </div>
        ) : null}
      </dl>
      <div className="decision-answer">
        {decision.answerable ? (
          <div className="answer-buttons no-print" role="group" aria-label="Dit svar">
            {ANSWERS.map((a) => (
              <button
                key={a.value}
                type="button"
                className={`answer-btn${answer === a.value ? " is-on" : ""}`}
                aria-pressed={answer === a.value}
                disabled={busy}
                onClick={() => choose(a.value)}
              >
                {a.label}
              </button>
            ))}
          </div>
        ) : (
          <span className="muted small no-print">Kan besvares, når Til OK er godkendt.</span>
        )}
        {answer && answeredAt ? (
          <span className="answer-given" role="status">
            Du svarede {answer} {shortDate(answeredAt)}
          </span>
        ) : (
          <span className="answer-given print-only">Ja / nej</span>
        )}
      </div>
      {error ? (
        <p className="cell-sub" role="alert">
          {error}
        </p>
      ) : null}
    </li>
  );
}
