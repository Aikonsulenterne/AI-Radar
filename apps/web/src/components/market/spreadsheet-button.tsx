"use client";

import { useState } from "react";
import { ApiClientError, downloadOkBriefSpreadsheet } from "../../app/lib/api";

/** Henter regnearket: radarens fund og formler. OK's tal skrives ind på
 * OK's egen pc — radaren ser dem aldrig. */
export function SpreadsheetButton() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const blob = await downloadOkBriefSpreadsheet();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "til-ok-regnestykke.xlsx";
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Kunne ikke hente regnearket.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <span>
      <button type="button" className="btn btn-secondary" onClick={run} disabled={busy}>
        {busy ? "Henter …" : "Regn på det i Excel"}
      </button>
      {error ? (
        <span className="cell-sub" role="alert">
          {error}
        </span>
      ) : null}
    </span>
  );
}
