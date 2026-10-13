"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ApiClientError, generateOkBrief } from "../../app/lib/api";

/** Admin: skriv Til OK igen ud fra de nuværende fund (sker også automatisk
 * efter hver kørsel med nye fund). */
export function GenerateBriefButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      await generateOkBrief();
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Kunne ikke opdatere. Prøv igen.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <span>
      <button type="button" className="btn btn-secondary" onClick={run} disabled={busy}>
        {busy ? "Skriver Til OK …" : "Opdatér Til OK"}
      </button>
      {error ? (
        <span className="cell-sub" role="alert">
          {error}
        </span>
      ) : null}
    </span>
  );
}
