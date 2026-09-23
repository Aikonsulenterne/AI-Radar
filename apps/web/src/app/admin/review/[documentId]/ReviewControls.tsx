"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ApiClientError,
  approveClaim,
  completeReview,
  markClaimNeedsCorroboration,
  processDocument,
  rejectClaim,
  relateClaim,
  type Claim,
  type ClaimRelation,
  type DocumentReview,
} from "../../../lib/api";

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof ApiClientError ? err.message : fallback;
}

export function DocumentControls({ document }: { document: DocumentReview }) {
  const router = useRouter();
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const canProcess = ["normalized", "classified_relevant", "failed"].includes(
    document.processing_status,
  );
  const canComplete = ["review_pending", "partially_reviewed"].includes(
    document.processing_status,
  );
  const openClaims = document.claims.filter(
    (c) =>
      c.review_status === "proposed" ||
      c.review_status === "needs_corroboration",
  );

  async function run(action: () => Promise<unknown>, fallback: string) {
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      await action();
      router.refresh();
    } catch (err) {
      setError(errorMessage(err, fallback));
    } finally {
      setBusy(false);
    }
  }

  async function handleProcess() {
    await run(async () => {
      const result = await processDocument(document.id);
      setStatus(
        `Behandling færdig: ${result.claims_created} claims foreslået` +
          (result.claims_skipped > 0
            ? `, ${result.claims_skipped} kasseret`
            : ""),
      );
    }, "AI-behandling fejlede.");
  }

  async function handleBatchApprove() {
    await run(async () => {
      for (const claim of openClaims) {
        await approveClaim(claim.id);
      }
      setStatus(`${openClaims.length} claims godkendt.`);
    }, "Batchgodkendelse fejlede.");
  }

  async function handleComplete() {
    await run(
      () => completeReview(document.id),
      "Review kunne ikke afsluttes.",
    );
  }

  return (
    <div className="review-controls">
      <div className="source-actions-buttons">
        {canProcess ? (
          <button
            type="button"
            className="btn"
            onClick={handleProcess}
            disabled={busy}
          >
            {busy ? "Arbejder…" : "Kør AI-behandling"}
          </button>
        ) : null}
        {canComplete && openClaims.length > 0 ? (
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleBatchApprove}
            disabled={busy}
          >
            Godkend alle åbne ({openClaims.length})
          </button>
        ) : null}
        {canComplete ? (
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleComplete}
            disabled={busy}
          >
            Afslut review
          </button>
        ) : null}
      </div>
      {status ? (
        <p className="action-status" role="status">
          {status}
        </p>
      ) : null}
      {error ? (
        <p className="alert-error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

/**
 * Dublet- og konfliktkandidater (Technical Master §15). Revieweren sætter den
 * endelige relation; ingen af de to claims slettes eller overskrives.
 */
export function DuplicateCandidates({ claim }: { claim: Claim }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const related = new Set(claim.relations.map((r) => r.related_claim_id));
  const open = claim.possible_duplicates.filter((c) => !related.has(c.id));
  if (open.length === 0) return null;

  async function relate(candidateId: string, relation: ClaimRelation) {
    setBusy(true);
    setError(null);
    try {
      await relateClaim(claim.id, candidateId, relation);
      router.refresh();
    } catch (err) {
      setError(errorMessage(err, "Relationen kunne ikke sættes."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="duplicate-candidates">
      <p className="cell-sub">
        {open.length === 1
          ? "1 mulig dublet eller konflikt"
          : `${open.length} mulige dubletter eller konflikter`}{" "}
        — samme subjekt, prædikat og objekt. Vurdér relationen; ingen af delene
        sletter noget.
      </p>
      {open.map((candidate) => (
        <div className="duplicate-candidate" key={candidate.id}>
          <p className="claim-statement">
            <b>{candidate.subject_name ?? "(ukendt subjekt)"}</b>{" "}
            <span className="claim-predicate">{candidate.predicate}</span>{" "}
            {candidate.object_display ?? <i>Ikke dokumenteret</i>}
          </p>
          <p className="cell-sub">
            Status: {candidate.review_status} · Livscyklus:{" "}
            {candidate.lifecycle_status}
          </p>
          <div className="source-actions-buttons">
            <button
              type="button"
              className="btn btn-secondary"
              disabled={busy}
              onClick={() => relate(candidate.id, "supersedes")}
            >
              Dublet — behold dette claim
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={busy}
              onClick={() => relate(candidate.id, "contradicts")}
            >
              Markér mulig konflikt
            </button>
          </div>
        </div>
      ))}
      {error ? (
        <p className="alert-error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function ClaimActions({ claim }: { claim: Claim }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(false);
  const [objectText, setObjectText] = useState(claim.object_text ?? "");

  const open =
    claim.review_status === "proposed" ||
    claim.review_status === "needs_corroboration";
  if (!open) return null;

  async function run(action: () => Promise<unknown>, fallback: string) {
    setBusy(true);
    setError(null);
    try {
      await action();
      router.refresh();
    } catch (err) {
      setError(errorMessage(err, fallback));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="claim-actions">
      {editing ? (
        <div className="claim-edit">
          <label htmlFor={`edit-${claim.id}`}>Ret objekt-tekst</label>
          <input
            id={`edit-${claim.id}`}
            value={objectText}
            onChange={(e) => setObjectText(e.target.value)}
          />
          <div className="source-actions-buttons">
            <button
              type="button"
              className="btn btn-secondary"
              disabled={busy}
              onClick={() =>
                run(
                  () =>
                    approveClaim(claim.id, { object_text: objectText || null }),
                  "Godkendelse fejlede.",
                )
              }
            >
              Ret og godkend
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setEditing(false)}
              disabled={busy}
            >
              Annullér
            </button>
          </div>
        </div>
      ) : (
        <div className="source-actions-buttons">
          <button
            type="button"
            className="btn btn-secondary"
            disabled={busy}
            onClick={() =>
              run(() => approveClaim(claim.id), "Godkendelse fejlede.")
            }
          >
            Godkend
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setEditing(true)}
            disabled={busy}
          >
            Ret og godkend
          </button>
          {claim.review_status === "proposed" ? (
            <button
              type="button"
              className="btn btn-secondary"
              disabled={busy}
              onClick={() =>
                run(
                  () => markClaimNeedsCorroboration(claim.id),
                  "Markeringen fejlede.",
                )
              }
            >
              Kræver yderligere dokumentation
            </button>
          ) : null}
          <button
            type="button"
            className="btn btn-secondary btn-danger"
            disabled={busy}
            onClick={() =>
              run(() => rejectClaim(claim.id), "Afvisning fejlede.")
            }
          >
            Afvis
          </button>
        </div>
      )}
      {error ? (
        <p className="alert-error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
