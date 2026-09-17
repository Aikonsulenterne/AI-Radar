"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ApiClientError,
  archiveCase,
  createCase,
  publishCase,
  type AdoptionCase,
  type Claim,
  type Company,
} from "../../lib/api";

export function CreateCaseForm({
  companies,
  approvedClaims,
}: {
  companies: Company[];
  approvedClaims: Claim[];
}) {
  const router = useRouter();
  const [companyId, setCompanyId] = useState(companies[0]?.id ?? "");
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const companyClaims = approvedClaims.filter(
    (claim) => claim.subject_entity_id === companyId,
  );

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
      await createCase({
        company_id: companyId,
        title,
        summary: summary || null,
        claim_ids: [...selected].filter((id) =>
          companyClaims.some((c) => c.id === id),
        ),
      });
      setTitle("");
      setSummary("");
      setSelected(new Set());
      router.refresh();
    } catch (err) {
      setError(
        err instanceof ApiClientError
          ? err.message
          : "Casen kunne ikke oprettes.",
      );
    } finally {
      setBusy(false);
    }
  }

  if (companies.length === 0) {
    return (
      <div className="empty-state">
        <p>
          <strong>Ingen virksomheder endnu.</strong>
        </p>
        <p>Virksomheder oprettes, når claims udtrækkes og godkendes.</p>
      </div>
    );
  }

  return (
    <form className="card form-grid" onSubmit={handleSubmit}>
      <h2 className="form-title">Opret case-udkast</h2>
      <div className="field field-narrow">
        <label htmlFor="case-company">Virksomhed</label>
        <select
          id="case-company"
          value={companyId}
          onChange={(e) => {
            setCompanyId(e.target.value);
            setSelected(new Set());
          }}
        >
          {companies.map((company) => (
            <option key={company.id} value={company.id}>
              {company.name}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label htmlFor="case-title">Titel</label>
        <input
          id="case-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          maxLength={300}
        />
      </div>
      <div className="field">
        <label htmlFor="case-summary">
          Potentiel læring (analyse, valgfri)
        </label>
        <textarea
          id="case-summary"
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          rows={2}
        />
      </div>

      <fieldset className="claim-picker">
        <legend>Faktagrundlag — godkendte claims for virksomheden</legend>
        {companyClaims.length === 0 ? (
          <p className="cell-sub">
            Ingen godkendte claims for den valgte virksomhed.
          </p>
        ) : (
          companyClaims.map((claim) => (
            <label key={claim.id} className="claim-picker-item">
              <input
                type="checkbox"
                checked={selected.has(claim.id)}
                onChange={() => toggleClaim(claim.id)}
              />
              <span>
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

export function CaseRowActions({
  adoptionCase,
}: {
  adoptionCase: AdoptionCase;
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

  return (
    <div className="source-actions">
      <div className="source-actions-buttons">
        {adoptionCase.status === "draft" ? (
          <button
            type="button"
            className="btn btn-secondary"
            disabled={busy}
            onClick={() =>
              run(() => publishCase(adoptionCase.id), "Publicering fejlede.")
            }
          >
            Publicér
          </button>
        ) : null}
        {adoptionCase.status === "published" ? (
          <button
            type="button"
            className="btn btn-secondary"
            disabled={busy}
            onClick={() =>
              run(() => archiveCase(adoptionCase.id), "Arkivering fejlede.")
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
