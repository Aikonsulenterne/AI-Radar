"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ApiClientError, putOkPublicStatus, type OkPublicStatusRow } from "../../app/lib/api";

type Stage = "drift" | "pilot" | "";

function Row({ row }: { row: OkPublicStatusRow }) {
  const router = useRouter();
  const [stage, setStage] = useState<Stage>(row.stage ?? "");
  const [url, setUrl] = useState(row.source_url ?? "");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const id = `ok-status-${row.technology_id}`;

  async function save() {
    setBusy(true);
    setMessage(null);
    try {
      await putOkPublicStatus(row.technology_id, {
        stage: stage || null,
        source_url: url.trim() || null,
      });
      setMessage("Gemt");
      router.refresh();
    } catch (err) {
      setMessage(err instanceof ApiClientError ? err.message : "Kunne ikke gemme.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="ok-status-row">
      <label htmlFor={`${id}-stage`}>{row.label}</label>
      <select id={`${id}-stage`} value={stage} onChange={(e) => setStage(e.target.value as Stage)}>
        <option value="">Ikke registreret</option>
        <option value="pilot">Pilot</option>
        <option value="drift">Drift</option>
      </select>
      <input
        aria-label={`Offentlig kilde for ${row.label}`}
        type="url"
        placeholder="https://www.ok.dk/…"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        disabled={stage === ""}
      />
      <button type="button" className="btn btn-secondary" onClick={save} disabled={busy}>
        Gem
      </button>
      {message ? (
        <span className="cell-sub" role="status">
          {message}
        </span>
      ) : null}
    </li>
  );
}

/** Admin: OK's egen række i konkurrentoverblikket. Kun offentligt kendt brug
 * med en offentlig kilde (fx en chatbot på ok.dk) — aldrig interne oplysninger. */
export function OkStatusForm({ rows }: { rows: OkPublicStatusRow[] }) {
  return (
    <ul className="ok-status-list">
      {rows.map((row) => (
        <Row key={row.technology_id} row={row} />
      ))}
    </ul>
  );
}
