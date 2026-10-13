"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiClientError, getMarketCases, listRuns, startRun } from "../../app/lib/api";

const POLL_MS = 10_000;
const WAKE_HINT =
  "API'et svarede ikke. Det kan være ved at vågne (op til et minut) – prøv igen om lidt.";

type Toast = { id: number; title: string; body: string };

/** Den ene primære handling på Kilder (designhandoff v2 §7). Bagefter vises
 * "N nye artikler læst · N nye cases fundet". */
export function UpdateRadarButton() {
  const router = useRouter();
  const [running, setRunning] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const casesBefore = useRef<number | null>(null);

  const toast = useCallback((title: string, body: string) => {
    const id = Date.now();
    setToasts((list) => [...list, { id, title, body }]);
    window.setTimeout(() => setToasts((list) => list.filter((t) => t.id !== id)), 6000);
  }, []);

  const countCases = useCallback(async () => {
    try {
      return (await getMarketCases({})).all_total;
    } catch {
      return null;
    }
  }, []);

  useEffect(() => {
    listRuns(1)
      .then((runs) => setRunning(runs[0]?.status === "running"))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(async () => {
      try {
        const [latest] = await listRuns(1);
        if (!latest || latest.status === "running") return;
        setRunning(false);
        if (latest.status === "failed") {
          toast("Opdateringen stoppede", latest.error_message_safe ?? "Prøv igen senere.");
        } else {
          const after = await countCases();
          const before = casesBefore.current;
          const found = after !== null && before !== null ? Math.max(after - before, 0) : null;
          toast(
            "Radaren er opdateret",
            `${latest.documents_created} nye artikler læst` +
              (found !== null ? ` · ${found} nye cases fundet` : ""),
          );
        }
        router.refresh();
      } catch {
        // Næste forsøg om lidt; API'et kan være ved at vågne.
      }
    }, POLL_MS);
    return () => window.clearInterval(timer);
  }, [running, countCases, router, toast]);

  async function start() {
    setRunning(true);
    casesBefore.current = await countCases();
    try {
      await startRun();
    } catch (err) {
      setRunning(false);
      toast(
        "Kunne ikke starte",
        err instanceof ApiClientError ? err.message : WAKE_HINT,
      );
    }
  }

  return (
    <>
      <button type="button" className="btn-primary" onClick={start} disabled={running}>
        {running ? "Opdaterer…" : "Opdatér radaren"}
      </button>
      <div className="toasts no-print" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className="toast">
            <div className="toast-title">{t.title}</div>
            <div className="toast-body">{t.body}</div>
          </div>
        ))}
      </div>
    </>
  );
}
