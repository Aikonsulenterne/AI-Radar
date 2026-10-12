import Link from "next/link";
import { getSignal, type SignalDetail } from "../../lib/api";
import {
  DOCUMENTATION_LABELS,
  documentationBadgeClass,
  formatDateTime,
} from "../../lib/labels";
import { AiPublishedBadge } from "../../../components/states/ai-badge";
import { ApiErrorAlert } from "../../../components/states/api-error";
import { FactGroups } from "../../../components/facts/fact-groups";

export const dynamic = "force-dynamic";

function factSummary(signal: SignalDetail): string {
  const companies = signal.companies.length;
  const documents = new Set(
    signal.claims.flatMap((claim) => claim.evidence.map((e) => e.document_id)),
  ).size;
  return [
    `${signal.claims.length} fakta`,
    companies > 0
      ? `${companies} ${companies === 1 ? "virksomhed" : "virksomheder"}`
      : null,
    `${documents} ${documents === 1 ? "kilde" : "kilder"}`,
  ]
    .filter(Boolean)
    .join(" · ");
}

export default async function SignalPage({
  params,
}: {
  params: Promise<{ signalId: string }>;
}) {
  const { signalId } = await params;
  let signal: SignalDetail | null = null;
  let loadError: unknown = null;
  try {
    signal = await getSignal(signalId);
  } catch (error) {
    signal = null;
    loadError = error;
  }

  if (signal === null) {
    return (
      <>
        <h1>Signal</h1>
        <ApiErrorAlert
          error={loadError}
          notFound="Signalet findes ikke, er arkiveret eller er ikke publiceret endnu."
        />
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
        {signal.auto_published ? (
          <>
            <AiPublishedBadge />{" "}
          </>
        ) : null}
        {signal.internal ? (
          <>
            <span className="badge badge-candidate">
              Intern analyse · OK&#8217;s egne data
            </span>{" "}
          </>
        ) : null}
        Publiceret {formatDateTime(signal.published_at)} · {signal.claim_count}{" "}
        godkendte fakta som grundlag
      </p>

      {/* Fakta, analyse og anbefaling adskilles semantisk og visuelt
          (Product Master §2). */}
      <section className="signal-section" aria-label="Resumé">
        <h2 className="section-title">Resumé</h2>
        <p>{signal.summary}</p>
      </section>

      <section
        className="signal-section section-fact"
        aria-label="Fakta og evidens"
      >
        <h2 className="section-title">
          Fakta <span className="section-tag">Dokumenteret fakta</span>
        </h2>
        <p className="cell-sub">{factSummary(signal)}</p>
        <FactGroups claims={signal.claims} />
      </section>

      {signal.analysis ? (
        <section
          className="signal-section signal-analysis"
          aria-label="Analyse"
        >
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
    </>
  );
}
