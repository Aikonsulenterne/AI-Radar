import Link from "next/link";
import { getDashboard, type Dashboard } from "./lib/api";
import {
  DOCUMENTATION_LABELS,
  documentationBadgeClass,
  formatDateTime,
} from "./lib/labels";

export const dynamic = "force-dynamic";

function KpiCard({
  value,
  label,
  definition,
}: {
  value: number | string;
  label: string;
  definition: string;
}) {
  return (
    <div className="kpi-card">
      <p className="kpi-value">{value}</p>
      <p className="kpi-label">{label}</p>
      <p className="kpi-definition">{definition}</p>
    </div>
  );
}

export default async function OverblikPage() {
  let dashboard: Dashboard | null = null;
  try {
    dashboard = await getDashboard();
  } catch {
    dashboard = null;
  }

  if (dashboard === null) {
    return (
      <>
        <h1>Overblik</h1>
        <div className="alert-error" role="alert">
          API&#8217;et kunne ikke nås. Start backenden og genindlæs siden.
        </div>
      </>
    );
  }

  const horizon = dashboard.technologies_by_horizon;

  return (
    <>
      <section className="hero" aria-label="Introduktion">
        <p className="hero-eyebrow">Technology Intelligence</p>
        <h1>Hvad gør de bedste — og hvor ved vi det fra?</h1>
        <p className="hero-sub">
          Verificerede signaler om AI-adoption i skandinaviske virksomheder.
          Hvert tal er en optælling i databasen, og hvert signal kan åbnes
          hele vejen ned til evidensuddrag og original kilde.
        </p>
      </section>

      <div className="kpi-grid">
        <KpiCard
          value={dashboard.published_signals}
          label="Publicerede signaler"
          definition="Signaler med status published"
        />
        <KpiCard
          value={dashboard.approved_claims}
          label="Godkendte claims"
          definition="Claims godkendt af reviewer"
        />
        <KpiCard
          value={dashboard.companies_with_claims}
          label="Virksomheder"
          definition="Med mindst ét godkendt claim"
        />
        <KpiCard
          value={dashboard.documents_in_review}
          label="Dokumenter i review"
          definition="Afventer claim-review"
        />
        <KpiCard
          value={`${horizon.now} / ${horizon.next} / ${horizon.horizon}`}
          label="Teknologier NU / NÆSTE / HORIZON"
          definition="Aktive teknologier pr. horisont"
        />
      </div>

      <h2 className="section-title">Seneste signaler</h2>
      {dashboard.latest_signals.length === 0 ? (
        <div className="empty-state">
          <p>
            <strong>Ingen publicerede signaler endnu.</strong>
          </p>
          <p>
            Signaler publiceres, når reviewede claims er samlet og godkendt i
            signalbyggeren.
          </p>
        </div>
      ) : (
        <div className="signal-list">
          {dashboard.latest_signals.map((signal) => (
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
                  <span className="cell-sub">
                    Publiceret {formatDateTime(signal.published_at)} ·{" "}
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
  );
}
