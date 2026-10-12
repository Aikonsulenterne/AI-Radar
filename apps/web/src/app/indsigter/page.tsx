import Link from "next/link";
import {
  getDecisionBrief,
  listInternalSignals,
  type DecisionFinding,
  type Signal,
} from "../lib/api";
import { formatDateTime } from "../lib/labels";
import { ApiErrorAlert } from "../../components/states/api-error";
import { AiPublishedBadge } from "../../components/states/ai-badge";
import { InternalUpload } from "./InternalUpload";

export const dynamic = "force-dynamic";

export default async function InsightsPage() {
  let signals: Signal[] | null = null;
  let findings: DecisionFinding[] = [];
  let loadError: unknown = null;
  try {
    const [internal, brief] = await Promise.all([
      listInternalSignals(),
      getDecisionBrief(),
    ]);
    signals = internal.items;
    findings = brief.brief.internal_findings;
  } catch (error) {
    loadError = error;
  }

  return (
    <>
      <section className="hero" aria-label="Introduktion">
        <p className="hero-eyebrow">Indsigter · intern</p>
        <h1>Hvad fortæller OK&#8217;s egne data?</h1>
        <p className="hero-sub">
          Analyser af OK Kundeservices egne tal — indbakker, opkald og sager.
          Holdes adskilt fra radarens markedsviden og vises kun her og i
          beslutningsoplægget.
        </p>
      </section>

      {signals === null ? (
        <ApiErrorAlert error={loadError} />
      ) : (
        <>
          <h2 className="section-title">Fund i egne data</h2>
          {findings.length === 0 ? (
            <p className="cell-sub">
              Ingen fund registreret endnu. Tilføj dem under{" "}
              <Link href="/admin/beslutningsoplaeg">
                Admin → OK-tal &amp; oplæg
              </Link>
              .
            </p>
          ) : (
            <div className="kpi-grid">
              {findings.map((finding) => (
                <div className="kpi-card" key={finding.title}>
                  <p className="kpi-value">{finding.figure ?? "–"}</p>
                  <p className="kpi-label">{finding.title}</p>
                  {finding.description ? (
                    <p className="kpi-definition">{finding.description}</p>
                  ) : null}
                </div>
              ))}
            </div>
          )}

          <h2 className="section-title">Interne analyser</h2>
          {signals.length === 0 ? (
            <p className="cell-sub">
              Ingen interne analyser endnu. Upload en eksport nedenfor.
            </p>
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
                      <span className="badge badge-candidate">
                        Intern analyse
                      </span>
                      {signal.auto_published ? <AiPublishedBadge /> : null}
                      <span className="cell-sub">
                        {formatDateTime(signal.published_at)} ·{" "}
                        {signal.claim_count} claims
                      </span>
                    </header>
                    <h3 className="signal-title">{signal.title}</h3>
                    <p className="signal-summary">{signal.summary}</p>
                  </article>
                </Link>
              ))}
            </div>
          )}
        </>
      )}

      <InternalUpload />
    </>
  );
}
