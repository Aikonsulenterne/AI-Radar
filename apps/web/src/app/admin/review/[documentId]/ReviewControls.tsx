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
  type Claim,
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
