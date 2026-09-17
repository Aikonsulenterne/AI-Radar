import Link from "next/link";
import { getSignal, type SignalDetail } from "../../lib/api";
import {
  DOCUMENTATION_LABELS,
  documentationBadgeClass,
  formatDateTime,
} from "../../lib/labels";

export const dynamic = "force-dynamic";

export default async function SignalPage({
  params,
}: {
  params: Promise<{ signalId: string }>;
}) {
  const { signalId } = await params;
  let signal: SignalDetail | null = null;
  try {
    signal = await getSignal(signalId);
  } catch {
    signal = null;
  }

  if (signal === null) {
    return (
      <>
        <h1>Signal</h1>
        <div className="alert-error" role="alert">
          Signalet kunne ikke hentes — det findes ikke, er ikke publiceret,
          eller API&#8217;et kører ikke.
        </div>
        <p>
          <Link href="/">Tilbage til Overblik</Link>
        </p>
      </>
    );
  }

  return (
    <>
      <p className="cell-sub">
        <Link href="/">← Overblik</Link>
      </p>
      <h1>{signal.title}</h1>
      <p className="page-lead">
        <span className={documentationBadgeClass(signal.documentation_level)}>
          {DOCUMENTATION_LABELS[signal.documentation_level]}
        </span>{" "}
        Publiceret {formatDateTime(signal.published_at)} ·{" "}
        {signal.claim_count} godkendte claims som faktagrundlag
      </p>

      {/* Fakta, analyse og anbefaling adskilles semantisk og visuelt
          (Product Master §2). */}
      <section className="signal-section" aria-label="Resumé">
        <h2 className="section-title">Resumé</h2>
        <p>{signal.summary}</p>
      </section>

      <section className="signal-section section-fact" aria-label="Fakta og evidens">
        <h2 className="section-title">
          Fakta <span className="section-tag">Dokumenteret fakta</span>
        </h2>
        {signal.claims.length === 0 ? (
          <p className="cell-sub">Ingen claims tilknyttet.</p>
        ) : (
          <div className="claim-list">
            {signal.claims.map((claim) => (
              <article className="claim-card" key={claim.id}>
                <p className="claim-statement">
                  <b>{claim.subject_name ?? "(ukendt subjekt)"}</b>{" "}
                  <span className="claim-predicate">{claim.predicate}</span>{" "}
                  {claim.object_name ?? claim.object_text ?? (
                    <i>Ikke dokumenteret</i>
                  )}
                </p>
                {claim.evidence.map((evidence) => (
                  <blockquote className="evidence-quote" key={evidence.id}>
                    &#8220;{evidence.supporting_excerpt}&#8221;
                    {evidence.source_type_snapshot ? (
                      <footer className="cell-sub">
                        Kildetype: {evidence.source_type_snapshot}
                      </footer>
                    ) : null}
                  </blockquote>
                ))}
              </article>
            ))}
          </div>
        )}
      </section>

      {signal.analysis ? (
        <section className="signal-section signal-analysis" aria-label="Analyse">
          <h2 className="section-title">
            Analyse <span className="section-tag">Analyse, ikke fakta</span>
          </h2>
          <p>{signal.analysis}</p>
        </section>
      ) : null}

      {signal.recommendation ? (
        <section
          className="signal-section signal-recommendation"
          aria-label="Anbefaling"
        >
          <h2 className="section-title">
            Anbefaling <span className="section-tag">Næste skridt</span>
          </h2>
          <p>{signal.recommendation}</p>
        </section>
      ) : null}

      {signal.companies.length > 0 || signal.technologies.length > 0 ? (
        <section className="signal-section" aria-label="Relaterede entiteter">
          <h2 className="section-title">Relateret</h2>
          <p>
            {signal.companies.length > 0 ? (
              <>Virksomheder: {signal.companies.map((c) => c.name).join(", ")}. </>
            ) : null}
            {signal.technologies.length > 0 ? (
              <>Teknologier: {signal.technologies.map((t) => t.name).join(", ")}.</>
            ) : null}
          </p>
        </section>
      ) : null}
    </>
  );
}
