"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ApiClientError,
  runSource,
  uploadDocument,
  type Source,
} from "../../lib/api";

export function SourceActions({ source }: { source: Source }) {
  const router = useRouter();
  const fileInput = useRef<HTMLInputElement>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const canRun =
    source.active &&
    source.retrieval_method === "web_fetch" &&
    source.access_class === "public";

  async function handleRun() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await runSource(source.id);
      setMessage(
        result.created
          ? "Nyt dokument hentet."
          : "Uændret indhold — kendt dokument.",
      );
      router.refresh();
    } catch (err) {
      setError(
        err instanceof ApiClientError ? err.message : "Hentning fejlede.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const result = await uploadDocument(source.id, file);
      setMessage(
        result.created
          ? "Dokument uploadet og normaliseret."
          : "Filen er allerede kendt (samme indhold).",
      );
      router.refresh();
    } catch (err) {
      setError(
        err instanceof ApiClientError ? err.message : "Upload fejlede.",
      );
    } finally {
      setBusy(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  return (
    <div className="source-actions">
      <div className="source-actions-buttons">
        {canRun ? (
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleRun}
            disabled={busy}
          >
            {busy ? "Arbejder…" : "Kør hentning"}
          </button>
        ) : null}
        {source.active ? (
          <>
            <label className="btn btn-secondary" htmlFor={`upload-${source.id}`}>
              Upload fil
            </label>
            <input
              ref={fileInput}
              id={`upload-${source.id}`}
              type="file"
              accept=".txt,.html,.pdf,text/plain,text/html,application/pdf"
              onChange={handleUpload}
              disabled={busy}
              className="visually-hidden-input"
            />
          </>
        ) : null}
      </div>
      {message ? (
        <p className="action-status" role="status">
          {message}
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
