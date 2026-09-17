import Link from "next/link";
import {
  listCases,
  listOpportunities,
  listSignals,
  type AdoptionCase,
  type Opportunity,
  type Signal,
} from "../lib/api";
import { DOCUMENTATION_LABELS, formatDateTime } from "../lib/labels";

export const dynamic = "force-dynamic";

export default async function BriefingPage() {
  let signals: Signal[] | null = null;
  let cases: AdoptionCase[] = [];
  let opportunities: Opportunity[] = [];
  try {
    const [signalPage, casePage, oppPage] = await Promise.all([
      listSignals(),
      listCases(),
      listOpportunities(),
    ]);
    signals = signalPage.items.filter((s) => s.status === "published");
    cases = casePage.items;
    opportunities = oppPage.items;
  } catch {
    signals = null;
  }

  if (signals === null) {
    return (
      <>
        <h1>Briefing</h1>
        <div className="alert-error" role="alert">
          API&#8217;et kunne ikke nås. Start backenden og genindlæs siden.
        </div>
      </>
    );
  }

  const topSignals = signals.slice(0, 3);
  const latestCases = cases.slice(0, 3);
  const nextSteps = opportunities
    .filter((o) => o.status !== "closed")
    .slice(0, 5);

  const empty =
    topSignals.length === 0 &&
    latestCases.length === 0 &&
    nextSteps.length === 0;

  return (
    <>
      <h1>Briefing</h1>
      <p className="page-lead">
        Genereret visning af publiceret intelligence. Alt kan spores tilbage
        til kilder via signal- og casedetaljerne.
      </p>

      {empty ? (
        <div className="empty-state">
          <p>
            <strong>Intet at briefe om endnu.</strong>
          </p>
          <p>
            Briefingen fyldes, når signaler og cases publiceres, og
            opportunities godkendes.
          </p>
        </div>
      ) : (
        <>
          <section className="signal-section" aria-label="Vigtigste udviklinger">
            <h2 className="section-title">Vigtigste udviklinger</h2>
            {topSignals.length === 0 ? (
              <p className="cell-sub">Ingen publicerede signaler.</p>
            ) : (
              <ul>
                {topSignals.map((signal) => (
                  <li key={signal.id}>
                    <Link href={`/signals/${signal.id}`}>{signal.title}</Link>{" "}
                    <span className="cell-sub">
                      {DOCUMENTATION_LABELS[signal.documentation_level]} ·{" "}
                      {formatDateTime(signal.published_at)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section
            className="signal-section"
            aria-label="Nye verificerede cases"
          >
            <h2 className="section-title">Nye verificerede cases</h2>
            {latestCases.length === 0 ? (
              <p className="cell-sub">Ingen publicerede cases.</p>
            ) : (
              <ul>
                {latestCases.map((adoptionCase) => (
                  <li key={adoptionCase.id}>
                    <Link href={`/adoption/cases/${adoptionCase.id}`}>
                      {adoptionCase.title}
                    </Link>{" "}
                    <span className="cell-sub">
                      {adoptionCase.company_name ?? ""}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section
            className="signal-section signal-recommendation"
            aria-label="Næste skridt"
          >
            <h2 className="section-title">
              Næste skridt <span className="section-tag">Anbefaling</span>
            </h2>
            {nextSteps.length === 0 ? (
              <p className="cell-sub">Ingen åbne opportunities.</p>
            ) : (
              <ol>
                {nextSteps.map((opportunity) => (
                  <li key={opportunity.id}>
                    <Link href={`/opportunities/${opportunity.id}`}>
                      {opportunity.title}
                    </Link>
                    : {opportunity.recommended_next_action}{" "}
                    <span className="cell-sub">
                      ({opportunity.approved ? "godkendt" : "kandidat"})
                    </span>
                  </li>
                ))}
              </ol>
            )}
          </section>

          <p className="cell-sub">
            Kilder og metode: <Link href="/sources">Source Registry</Link>.
            Hver observation kan åbnes tilbage til dokumentation.
          </p>
        </>
      )}
    </>
  );
}
