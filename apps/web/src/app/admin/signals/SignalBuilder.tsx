"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ApiClientError,
  archiveSignal,
  createSignal,
  publishSignal,
  type Claim,
  type DocumentationLevel,
  type Signal,
} from "../../lib/api";
import { DOCUMENTATION_LABELS } from "../../lib/labels";

const LEVELS: DocumentationLevel[] = [
  "strong",
  "limited",
  "early",
  "conflicting",
];

export function CreateSignalForm({
  approvedClaims,
}: {
  approvedClaims: Claim[];
}) {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [analysis, setAnalysis] = useState("");
  const [recommendation, setRecommendation] = useState("");
  const [level, setLevel] = useState<DocumentationLevel>("limited");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function toggleClaim(id: string) {
    setSelected((prev) => {
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
      await createSignal({
        title,
        summary,
        analysis: analysis || null,
        recommendation: recommendation || null,
        documentation_level: level,
        claim_ids: [...selected],
      });
      setTitle("");
      setSummary("");
      setAnalysis("");
      setRecommendation("");
      setSelected(new Set());
      router.refresh();
    } catch (err) {
      setError(
        err instanceof ApiClientError
          ? err.message
          : "Signalet kunne ikke oprettes.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card form-grid" onSubmit={handleSubmit}>
      <h2 className="form-title">Opret signaludkast</h2>
      <div className="field">
        <label htmlFor="signal-title">Titel</label>
        <input
          id="signal-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          maxLength={300}
        />
      </div>
      <div className="field">
        <label htmlFor="signal-summary">Resumé (fakta-nært)</label>
        <textarea
          id="signal-summary"
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          required
          rows={2}
        />
      </div>
      <div className="field">
        <label htmlFor="signal-analysis">Analyse (fortolkning, valgfri)</label>
        <textarea
          id="signal-analysis"
          value={analysis}
          onChange={(e) => setAnalysis(e.target.value)}
          rows={2}
        />
      </div>
      <div className="field">
        <label htmlFor="signal-recommendation">Anbefaling (valgfri)</label>
        <textarea
          id="signal-recommendation"
          value={recommendation}
          onChange={(e) => setRecommendation(e.target.value)}
          rows={2}
        />
      </div>
      <div className="field field-narrow">
        <label htmlFor="signal-level">Dokumentationsstyrke</label>
        <select
          id="signal-level"
          value={level}
          onChange={(e) => setLevel(e.target.value as DocumentationLevel)}
        >
          {LEVELS.map((l) => (
            <option key={l} value={l}>
              {DOCUMENTATION_LABELS[l]}
            </option>
          ))}
        </select>
      </div>

      <fieldset className="claim-picker">
        <legend>Faktagrundlag — vælg godkendte claims</legend>
        {approvedClaims.length === 0 ? (
          <p className="cell-sub">
            Ingen godkendte claims endnu. Godkend claims i review, før et
            signal kan publiceres.
          </p>
        ) : (
          approvedClaims.map((claim) => (
            <label key={claim.id} className="claim-picker-item">
              <input
                type="checkbox"
                checked={selected.has(claim.id)}
                onChange={() => toggleClaim(claim.id)}
              />
              <span>
                <b>{claim.subject_name}</b>{" "}
                <span className="claim-predicate">{claim.predicate}</span>{" "}
                {claim.object_name ?? claim.object_text ?? ""}
              </span>
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
          {busy ? "Opretter…" : "Gem som kladde"}
        </button>
      </div>
    </form>
  );
}

export function SignalRowActions({ signal }: { signal: Signal }) {
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

  return (
    <div className="source-actions">
      <div className="source-actions-buttons">
        {signal.status === "draft" ? (
          <button
            type="button"
            className="btn btn-secondary"
            disabled={busy}
            onClick={() =>
              run(() => publishSignal(signal.id), "Publicering fejlede.")
            }
          >
            Publicér
          </button>
        ) : null}
        {signal.status === "published" ? (
          <button
            type="button"
            className="btn btn-secondary"
            disabled={busy}
            onClick={() =>
              run(() => archiveSignal(signal.id), "Arkivering fejlede.")
            }
          >
            Arkivér
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
