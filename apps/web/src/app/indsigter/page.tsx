import Link from "next/link";
import { getInsights, type Insight, type InsightsData } from "../lib/api";
import { formatDateTime } from "../lib/labels";
import { ApiErrorAlert } from "../../components/states/api-error";
import { AiPublishedBadge } from "../../components/states/ai-badge";
import { GenerateButton } from "./GenerateButton";

export const dynamic = "force-dynamic";

const TYPE_LABELS: Record<Insight["type"], string> = {
  adoption: "Adoption",
  vendor_move: "Leverandørbevægelse",
  effect: "Dokumenteret effekt",
  barrier: "Barriere",
  gap: "Hul i markedet",
  new_tech: "Ny teknologi",
};

const STRENGTH_LABELS: Record<Insight["strength"], string> = {
  stærk: "Stærk evidens",
  moderat: "Moderat evidens",
  svag: "Svag evidens",
};

function strengthClass(strength: Insight["strength"]): string {
  if (strength === "stærk") return "badge badge-ok";
  if (strength === "moderat") return "badge badge-warn";
  return "badge badge-danger";
}

function InsightCard({ insight }: { insight: Insight }) {
  return (
    <article className="problem-card" aria-label={insight.title}>
      <header className="claim-card-header">
        <span className="badge">{TYPE_LABELS[insight.type]}</span>
        <span className={strengthClass(insight.strength)}>
          {STRENGTH_LABELS[insight.strength]}
        </span>
        <AiPublishedBadge />
        <span className="cell-sub">
          {insight.document_count} dokumenter
          {insight.vendor_only ? " · kun leverandørernes egne kilder" : ""}
          {insight.problem ? (
            <>
              {" · "}
              <Link href="/muligheder">{insight.problem}</Link>
            </>
          ) : null}
        </span>
      </header>
      <h2>{insight.title}</h2>

      <section className="signal-section section-fact" aria-label="Fakta">
        <h3 className="section-title">
          Fakta <span className="section-tag">Fra de citerede kilder</span>
        </h3>
        <p>{insight.finding}</p>
      </section>
      {insight.implication ? (
        <section
          className="signal-section signal-analysis"
          aria-label="Analyse"
        >
          <h3 className="section-title">
            Hvad det betyder for OK{" "}
            <span className="section-tag">Analyse, ikke fakta</span>
          </h3>
          <p>{insight.implication}</p>
        </section>
      ) : null}
      {insight.recommendation ? (
        <section
          className="signal-section signal-recommendation"
          aria-label="Anbefaling"
        >
          <h3 className="section-title">
            Næste skridt <span className="section-tag">Anbefaling</span>
          </h3>
          <p>{insight.recommendation}</p>
        </section>
      ) : null}

      <details>
        <summary>Se evidensen ({insight.evidence.length} claims)</summary>
        <ul className="offering-list">
          {insight.evidence.map((evidence) => (
            <li key={evidence.claim_id}>
              <strong>{evidence.statement}</strong>
              {evidence.excerpt ? (
                <p className="offering-excerpt">
                  &ldquo;{evidence.excerpt}&rdquo;
                </p>
              ) : null}
              <span className="cell-sub">
                {evidence.vendor_source ? "Leverandørens eget udsagn · " : ""}
                {evidence.source_url ? (
                  <a
                    href={evidence.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {evidence.source_name ?? "Kilde"} ↗
                  </a>
                ) : (
                  (evidence.source_name ?? "")
                )}
              </span>
            </li>
          ))}
        </ul>
      </details>
    </article>
  );
}

export default async function InsightsPage() {
  let insights: InsightsData | null = null;
  let loadError: unknown = null;
  try {
    insights = await getInsights();
  } catch (error) {
    loadError = error;
  }

  return (
    <>
      <section className="hero" aria-label="Introduktion">
        <p className="hero-eyebrow">Indsigter</p>
        <h1>Hvad viser radarens fund — samlet set?</h1>
        <p className="hero-sub">
          Mønstre, der først bliver synlige, når mange kilder læses sammen: hvem
          der tager hvad i brug, hvor leverandørerne bevæger sig, og hvad der
          virker. Hver indsigt bygger på mindst to kilder og kan åbnes ned til
          citaterne.
        </p>
      </section>

      {insights === null ? (
        <ApiErrorAlert error={loadError} />
      ) : (
        <>
          <p className="cell-sub">
            {insights.generated_at
              ? `Genereret ${formatDateTime(insights.generated_at)} ud fra ${insights.evidence_count} godkendte claims` +
                (insights.discarded > 0
                  ? ` · ${insights.discarded} forslag kasseret, fordi de byggede på for få kilder`
                  : "")
              : "Ingen indsigter genereret endnu."}
          </p>
          <GenerateButton />
          {insights.items.length === 0 ? (
            <div className="empty-state">
              <p>
                <strong>Ingen indsigter endnu.</strong>
              </p>
              <p>
                Indsigter kræver fund fra flere kilder. De dannes automatisk
                efter kørsler, når radaren har nok dokumentation.
              </p>
            </div>
          ) : (
            insights.items.map((insight) => (
              <InsightCard key={insight.id} insight={insight} />
            ))
          )}
        </>
      )}
    </>
  );
}
