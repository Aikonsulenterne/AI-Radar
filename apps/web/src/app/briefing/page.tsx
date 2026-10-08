import Link from "next/link";
import {
  getVendorLandscape,
  listCases,
  listOpportunities,
  listSignals,
  listTechnologies,
  type AdoptionCase,
  type Opportunity,
  type Signal,
  type Technology,
  type VendorLandscape,
} from "../lib/api";
import { DOCUMENTATION_LABELS, formatDateTime } from "../lib/labels";
import { ApiErrorAlert } from "../../components/states/api-error";

export const dynamic = "force-dynamic";

// Briefingens tidsvindue for nye tilbud og nye capabilities.
const RECENT_DAYS = 30;

type RecentOffering = {
  key: string;
  vendor: string;
  product: string;
  capability: string;
  technologyId: string | null;
  observedAt: string;
};

function recentOfferings(landscape: VendorLandscape, since: number): RecentOffering[] {
  const rows: RecentOffering[] = [];
  for (const capability of landscape.capabilities) {
    for (const vendor of capability.vendors) {
      for (const offering of vendor.offerings) {
        if (!offering.observed_at) continue;
        if (new Date(offering.observed_at).getTime() < since) continue;
        rows.push({
          key: offering.claim_id,
          vendor: vendor.name,
          product: offering.product ?? "Produkt ikke navngivet",
          capability: capability.capability_name,
          technologyId: capability.technology?.id ?? null,
          observedAt: offering.observed_at,
        });
      }
    }
  }
  return rows.sort((a, b) => b.observedAt.localeCompare(a.observedAt)).slice(0, 8);
}

export default async function BriefingPage() {
  let signals: Signal[] | null = null;
  let loadError: unknown = null;
  let cases: AdoptionCase[] = [];
  let opportunities: Opportunity[] = [];
  let offerings: RecentOffering[] = [];
  let newTechnologies: Technology[] = [];
  try {
    const [signalPage, casePage, oppPage, landscape, techPage] = await Promise.all([
      listSignals(),
      listCases(),
      listOpportunities(),
      getVendorLandscape(),
      listTechnologies(),
    ]);
    signals = signalPage.items.filter((s) => s.status === "published");
    cases = casePage.items;
    opportunities = oppPage.items;
    const since = Date.now() - RECENT_DAYS * 24 * 60 * 60 * 1000;
    offerings = recentOfferings(landscape, since);
    newTechnologies = techPage.items.filter(
      (t) =>
        t.is_candidate &&
        t.discovered_at !== null &&
        new Date(t.discovered_at).getTime() >= since,
    );
  } catch (error) {
    signals = null;
    loadError = error;
  }

  if (signals === null) {
    return (
      <>
        <h1>Briefing</h1>
        <ApiErrorAlert error={loadError} />
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
    nextSteps.length === 0 &&
    offerings.length === 0 &&
    newTechnologies.length === 0;

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
            aria-label="Nye leverandørtilbud"
          >
            <h2 className="section-title">
              Nye leverandørtilbud{" "}
              <span className="section-tag">Seneste {RECENT_DAYS} dage</span>
            </h2>
            {offerings.length === 0 ? (
              <p className="cell-sub">Ingen nye dokumenterede tilbud.</p>
            ) : (
              <ul>
                {offerings.map((offering) => (
                  <li key={offering.key}>
                    <strong>{offering.vendor}</strong>: {offering.product}{" "}
                    <span className="cell-sub">
                      {offering.technologyId ? (
                        <Link href={`/technologies/${offering.technologyId}`}>
                          {offering.capability}
                        </Link>
                      ) : (
                        offering.capability
                      )}{" "}
                      · {formatDateTime(offering.observedAt)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <p className="cell-sub">
              <Link href="/vendors">Hele leverandørlandskabet →</Link>
            </p>
          </section>

          <section className="signal-section" aria-label="Nyt i markedet">
            <h2 className="section-title">
              Nyt i markedet{" "}
              <span className="section-tag">Ikke kurateret</span>
            </h2>
            {newTechnologies.length === 0 ? (
              <p className="cell-sub">
                Ingen nye capabilities fundet de seneste {RECENT_DAYS} dage.
              </p>
            ) : (
              <ul>
                {newTechnologies.map((technology) => (
                  <li key={technology.id}>
                    <Link href={`/technologies/${technology.id}`}>
                      {technology.name}
                    </Link>{" "}
                    <span className="cell-sub">
                      Fundet {formatDateTime(technology.discovered_at)} ·{" "}
                      {technology.vendor_count} leverandør(er)
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
