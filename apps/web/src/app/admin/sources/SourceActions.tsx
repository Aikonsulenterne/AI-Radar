"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ApiClientError,
  runSource,
  uploadDocument,
  type RunFailure,
  type RunResult,
  type Source,
} from "../../lib/api";

function documents(count: number): string {
  return count === 1 ? "1 dokument" : `${count} dokumenter`;
}

function runSummary(result: RunResult): string {
  const parts: string[] = [];
  if (result.created_count > 0) {
    parts.push(`${documents(result.created_count)} hentet`);
  }
  if (result.unchanged_count > 0) {
    parts.push(`${documents(result.unchanged_count)} uændret`);
  }
  if (result.failures.length > 0) {
    const links = result.failures.length === 1 ? "1 link" : `${result.failures.length} links`;
    parts.push(`${links} kunne ikke hentes`);
  }
  return parts.length > 0 ? `${parts.join(", ")}.` : "Kørslen gav ingen dokumenter.";
}

export function SourceActions({ source }: { source: Source }) {
  const router = useRouter();
  const fileInput = useRef<HTMLInputElement>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [failures, setFailures] = useState<RunFailure[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const canRun =
    source.active &&
    (source.retrieval_method === "web_fetch" ||
      source.retrieval_method === "rss") &&
    source.access_class === "public";

  async function handleRun() {
    setBusy(true);
    setError(null);
    setMessage(null);
    setFailures([]);
    try {
      const result = await runSource(source.id);
      setMessage(runSummary(result));
      setFailures(result.failures);
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
    setFailures([]);
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
      {failures.length > 0 ? (
        <ul className="run-failures">
          {failures.map((failure, index) => (
            <li key={`${failure.url}-${index}`}>
              <span className="run-failure-url">{failure.url || "Entry uden link"}</span>
              <span className="run-failure-message">{failure.message}</span>
            </li>
          ))}
        </ul>
      ) : null}
      {error ? (
        <p className="alert-error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
