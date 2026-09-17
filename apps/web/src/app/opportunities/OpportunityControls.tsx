"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ApiClientError,
  approveOpportunity,
  createOpportunity,
  setOpportunityStatus,
  type Opportunity,
  type OpportunityStatus,
  type Problem,
  type Signal,
} from "../lib/api";

export const STATUS_LABELS: Record<OpportunityStatus, string> = {
  identified: "Identificeret",
  investigating: "Undersøges",
  business_case: "Business case",
  pilot: "Pilot",
  scaling: "Skalering",
  closed: "Afsluttet",
};

const STATUS_ORDER: OpportunityStatus[] = [
  "identified",
  "investigating",
  "business_case",
  "pilot",
  "scaling",
  "closed",
];

export function CreateOpportunityForm({
  problems,
  signals,
}: {
  problems: Problem[];
  signals: Signal[];
}) {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [problemId, setProblemId] = useState(problems[0]?.id ?? "");
  const [hypothesis, setHypothesis] = useState("");
  const [gaps, setGaps] = useState("");
  const [nextAction, setNextAction] = useState("");
  const [selectedSignals, setSelectedSignals] = useState<Set<string>>(
    new Set(),
  );
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function toggleSignal(id: string) {
    setSelectedSignals((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await createOpportunity({
        title,
        problem_id: problemId,
        relevance_hypothesis: hypothesis,
        evidence_gaps: gaps || null,
        recommended_next_action: nextAction,
        signal_ids: [...selectedSignals],
      });
      setTitle("");
      setHypothesis("");
      setGaps("");
      setNextAction("");
      setSelectedSignals(new Set());
      router.refresh();
    } catch (err) {
      setError(
        err instanceof ApiClientError
          ? err.message
          : "Opportunity'en kunne ikke oprettes (kræver Reviewer/Admin).",
      );
    } finally {
      setBusy(false);
    }
  }

  if (problems.length === 0) {
    return (
      <div className="empty-state">
        <p>
          <strong>Problem-taxonomien er tom.</strong>
        </p>
        <p>Indlæs seed-data (supabase/seed.sql), før opportunities oprettes.</p>
      </div>
    );
  }

  return (
    <form className="card form-grid" onSubmit={handleSubmit}>
      <h2 className="form-title">Opret opportunity-kandidat</h2>
      <div className="field">
        <label htmlFor="opp-title">Titel</label>
        <input
          id="opp-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          maxLength={300}
        />
      </div>
      <div className="field field-narrow">
        <label htmlFor="opp-problem">OK-problem</label>
        <select
          id="opp-problem"
          value={problemId}
          onChange={(e) => setProblemId(e.target.value)}
        >
          {problems.map((problem) => (
            <option key={problem.id} value={problem.id}>
              {problem.name}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="opp-hypothesis">Relevanshypotese</label>
        <textarea
          id="opp-hypothesis"
          value={hypothesis}
          onChange={(e) => setHypothesis(e.target.value)}
          required
          rows={2}
        />
      </div>
      <div className="field">
        <label htmlFor="opp-gaps">Evidenshuller (valgfri)</label>
        <textarea
          id="opp-gaps"
          value={gaps}
          onChange={(e) => setGaps(e.target.value)}
          rows={2}
        />
      </div>
      <div className="field">
        <label htmlFor="opp-action">Anbefalet næste handling</label>
        <textarea
          id="opp-action"
          value={nextAction}
          onChange={(e) => setNextAction(e.target.value)}
          required
          rows={2}
        />
      </div>

      <fieldset className="claim-picker">
        <legend>Relaterede signaler (ekstern evidens)</legend>
        {signals.length === 0 ? (
          <p className="cell-sub">Ingen publicerede signaler endnu.</p>
        ) : (
          signals.map((signal) => (
            <label key={signal.id} className="claim-picker-item">
              <input
                type="checkbox"
                checked={selectedSignals.has(signal.id)}
                onChange={() => toggleSignal(signal.id)}
              />
              <span>{signal.title}</span>
            </label>
          ))
        )}
      </fieldset>

      {error ? (
        <p className="alert-error" role="alert">
          {error}
        </p>
      ) : null}
      <div>
        <button type="submit" className="btn" disabled={busy}>
          {busy ? "Opretter…" : "Opret kandidat"}
        </button>
      </div>
    </form>
  );
}

export function OpportunityActions({
  opportunity,
}: {
  opportunity: Opportunity;
}) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function run(action: () => Promise<unknown>, fallback: string) {
    setBusy(true);
    setError(null);
    try {
      await action();
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : fallback);
    } finally {
      setBusy(false);
    }
  }

  const currentIndex = STATUS_ORDER.indexOf(opportunity.status);
  const nextStatus = STATUS_ORDER[currentIndex + 1];

  return (
    <div className="source-actions">
      <div className="source-actions-buttons">
        {!opportunity.approved ? (
          <button
            type="button"
            className="btn btn-secondary"
            disabled={busy}
            onClick={() =>
              run(
                () => approveOpportunity(opportunity.id),
                "Godkendelse fejlede.",
              )
            }
          >
            Godkend kandidat
          </button>
        ) : null}
        {opportunity.approved && nextStatus ? (
          <button
            type="button"
            className="btn btn-secondary"
            disabled={busy}
            onClick={() =>
              run(
                () => setOpportunityStatus(opportunity.id, nextStatus),
                "Statusskift fejlede.",
              )
            }
          >
            Ryk til {STATUS_LABELS[nextStatus]}
          </button>
        ) : null}
      </div>
      {error ? (
        <p className="alert-error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
