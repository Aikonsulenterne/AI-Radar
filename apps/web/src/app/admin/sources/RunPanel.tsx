"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ApiClientError,
  listRuns,
  startRun,
  type WorkerRun,
} from "../../lib/api";

const TRIGGER_LABELS: Record<WorkerRun["trigger"], string> = {
  schedule: "Ugentlig",
  manual: "Kør nu",
  cli: "Kommandolinje",
};

const STATUS_LABELS: Record<WorkerRun["status"], string> = {
  running: "Kører",
  succeeded: "Gennemført",
  failed: "Fejlet",
};

function statusClass(status: WorkerRun["status"]): string {
  if (status === "succeeded") return "badge badge-ok";
  if (status === "failed") return "badge badge-danger";
  return "badge badge-warn";
}

function formatDate(value: string | null): string {
  if (!value) return "–";
  return new Intl.DateTimeFormat("da-DK", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Europe/Copenhagen",
  }).format(new Date(value));
}

function summary(run: WorkerRun): string {
  const parts = [
    `${run.sources_checked} kilder kontrolleret`,
    `${run.documents_created} nye dokumenter`,
    `${run.documents_processed} AI-behandlet`,
  ];
  if (run.fetch_failures > 0) parts.push(`${run.fetch_failures} hentefejl`);
  if (run.processing_skipped_no_ai) parts.push("AI ikke konfigureret");
  return parts.join(" · ");
}

// Mens en kørsel er i gang, hentes status igen med dette interval.
const POLL_MS = 10_000;

/**
 * Automatisk kørsel: hent alle aktive kilder og AI-behandl nye dokumenter.
 * Den ugentlige kørsel udløses af GitHub Actions; knappen gør det samme on
 * demand. Kørslen foreslår kun claims — godkendelse sker fortsat i Review.
 */
export function RunPanel() {
  const router = useRouter();
  const [runs, setRuns] = useState<WorkerRun[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setRuns(await listRuns());
    } catch (err) {
      setError(
        err instanceof ApiClientError ? err.message : "Kørsler kunne ikke hentes.",
      );
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const running = runs?.some((run) => run.status === "running") ?? false;

  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(async () => {
      await refresh();
    }, POLL_MS);
    return () => window.clearInterval(timer);
  }, [running, refresh]);

  // Når en kørsel bliver færdig, opdateres kildelisten (senest kontrolleret).
  const [wasRunning, setWasRunning] = useState(false);
  useEffect(() => {
    if (wasRunning && !running) router.refresh();
    setWasRunning(running);
  }, [running, wasRunning, router]);

  async function handleStart() {
    setBusy(true);
    setError(null);
    try {
      await startRun();
      await refresh();
    } catch (err) {
      setError(
        err instanceof ApiClientError ? err.message : "Kørslen kunne ikke startes.",
      );
    } finally {
      setBusy(false);
    }
  }

  const latest = runs?.[0] ?? null;

  return (
    <section className="card" aria-labelledby="run-panel-title">
      <h2 className="form-title" id="run-panel-title">
        Automatisk kørsel
      </h2>
      <p className="page-lead">
        Henter RSS- og web-kilder og AI-behandler nye dokumenter. Kører
        automatisk hver mandag morgen for kilder, hvis frekvens er forfalden;
        &#8220;Kør nu&#8221; henter alle aktive kilder med det samme. Claims
        lander som forslag i Review — intet publiceres uden menneskelig
        godkendelse.
      </p>

      <button
        type="button"
        className="btn"
        onClick={handleStart}
        disabled={busy || running}
      >
        {running ? "Kører…" : busy ? "Starter…" : "Kør nu"}
      </button>

      {error ? (
        <p className="alert-error" role="alert">
          {error}
        </p>
      ) : null}

      {latest ? (
        <div className="run-latest" role="status">
          <p>
            <span className={statusClass(latest.status)}>
              {STATUS_LABELS[latest.status]}
            </span>{" "}
            Seneste kørsel: {TRIGGER_LABELS[latest.trigger]}, startet{" "}
            {formatDate(latest.started_at)}
            {latest.finished_at ? `, færdig ${formatDate(latest.finished_at)}` : ""}
          </p>
          <p className="cell-sub">{summary(latest)}</p>
          {latest.error_message_safe ? (
            <p className="alert-error">{latest.error_message_safe}</p>
          ) : null}
        </div>
      ) : runs !== null ? (
        <p className="cell-sub">Ingen kørsler endnu.</p>
      ) : null}

      {runs && runs.length > 1 ? (
        <details className="run-history">
          <summary>Tidligere kørsler</summary>
          <ul>
            {runs.slice(1).map((run) => (
              <li key={run.id}>
                <span className={statusClass(run.status)}>
                  {STATUS_LABELS[run.status]}
                </span>{" "}
                {formatDate(run.started_at)} · {TRIGGER_LABELS[run.trigger]} ·{" "}
                {summary(run)}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
    </section>
  );
}
