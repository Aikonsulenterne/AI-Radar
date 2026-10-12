"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ApiClientError, generateInsights } from "../lib/api";

/** Admin: generér indsigter nu (kørslerne gør det også automatisk). */
export function GenerateButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    setMessage("Analyserer radarens fund — det kan tage et par minutter …");
    try {
      const result = await generateInsights();
      setMessage(
        `Færdig: ${result.items.length} indsigter ud fra ${result.evidence_count} claims` +
          (result.discarded > 0
            ? ` (${result.discarded} kasseret for svag evidens).`
            : "."),
      );
      router.refresh();
    } catch (err) {
      setMessage(null);
      setError(
        err instanceof ApiClientError
          ? err.message
          : "Indsigterne kunne ikke genereres.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="no-print">
      <button
        type="button"
        className="btn btn-secondary"
        disabled={busy}
        onClick={() => void run()}
      >
        Generér indsigter nu
      </button>{" "}
      <span className="cell-sub">
        Kræver Admin. Sker også automatisk efter hver kørsel.
      </span>
      {message ? (
        <p className="cell-sub" role="status">
          {message}
        </p>
      ) : null}
      {error ? (
        <div className="alert-error" role="alert">
          {error}
        </div>
      ) : null}
    </div>
  );
}
