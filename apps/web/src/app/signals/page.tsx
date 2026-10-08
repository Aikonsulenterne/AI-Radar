import Link from "next/link";
import { listPublishedSignals, type Signal } from "../lib/api";
import {
  DOCUMENTATION_LABELS,
  documentationBadgeClass,
  formatDateTime,
} from "../lib/labels";
import { ApiErrorAlert } from "../../components/states/api-error";
import { AiPublishedBadge } from "../../components/states/ai-badge";

export const dynamic = "force-dynamic";

export default async function SignalsPage() {
  let signals: Signal[] | null = null;
  let total = 0;
  let loadError: unknown = null;
  try {
    const page = await listPublishedSignals();
    signals = page.items;
    total = page.total;
  } catch (error) {
    signals = null;
    loadError = error;
  }

  if (signals === null) {
    return (
      <>
        <h1>Signaler</h1>
        <ApiErrorAlert error={loadError} />
      </>
    );
  }

  return (
    <>
      <h1>Signaler</h1>
      <p className="page-lead">
        Alle publicerede signaler, nyeste først ({total}). Hvert signal kan
        åbnes ned til claims, evidensuddrag og original kilde.
      </p>
      {signals.length === 0 ? (
        <div className="empty-state">
          <p>
            <strong>Ingen publicerede signaler endnu.</strong>
          </p>
        </div>
      ) : (
        <div className="signal-list">
          {signals.map((signal) => (
            <Link
              key={signal.id}
              href={`/signals/${signal.id}`}
              className="signal-card-link"
            >
              <article className="signal-card">
                <header className="claim-card-header">
                  <span
                    className={documentationBadgeClass(
                      signal.documentation_level,
                    )}
                  >
                    {DOCUMENTATION_LABELS[signal.documentation_level]}
                  </span>
                  {signal.auto_published ? <AiPublishedBadge /> : null}
                  <span className="cell-sub">
                    Publiceret {formatDateTime(signal.published_at)} ·{" "}
                    {signal.claim_count} claims
                  </span>
                </header>
                <h2 className="signal-title">{signal.title}</h2>
                <p className="signal-summary">{signal.summary}</p>
              </article>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}
