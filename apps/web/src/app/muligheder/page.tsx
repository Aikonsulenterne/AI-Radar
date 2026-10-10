import Link from "next/link";
import { getOpportunityMap, type ProblemOpportunity } from "../lib/api";
import { ApiErrorAlert } from "../../components/states/api-error";
import { HorizonBadge } from "../../components/states/horizon-badge";

export const dynamic = "force-dynamic";

function ProblemCard({ problem }: { problem: ProblemOpportunity }) {
  const empty =
    problem.vendors.length === 0 &&
    problem.references.length === 0 &&
    problem.effects.length === 0;
  return (
    <article className="problem-card" aria-label={problem.name}>
      <h2>{problem.name}</h2>
      <p className="page-lead">{problem.description}</p>

      <div
        className="problem-capabilities"
        aria-label="Teknologier, der adresserer udfordringen"
      >
        {problem.capabilities.map((technology) => (
          <Link key={technology.id} href={`/technologies/${technology.id}`}>
            <HorizonBadge technology={technology} /> {technology.name}
          </Link>
        ))}
      </div>

      {empty ? (
        <p className="cell-sub">
          Radaren har endnu ingen dokumentation for denne udfordring. Den
          fyldes, efterhånden som kørslerne finder tilbud og erfaringer.
        </p>
      ) : (
        <div className="opportunity-grid">
          <section aria-label="Leverandører">
            <h3>Leverandører</h3>
            {problem.vendors.length === 0 ? (
              <p className="cell-sub">Ingen dokumenterede tilbud endnu.</p>
            ) : (
              <ul>
                {problem.vendors.slice(0, 6).map((vendor) => (
                  <li key={vendor.company_id}>
                    <strong>{vendor.name}</strong>
                    {vendor.nordic_documented ? (
                      <span className="badge badge-ok">
                        {" "}
                        Danmark/Norden dokumenteret
                      </span>
                    ) : null}
                    <span className="cell-sub">
                      {vendor.products.slice(0, 2).join(" · ") ||
                        vendor.capabilities.join(", ")}
                    </span>
                    {vendor.customers.length > 0 ? (
                      <span className="cell-sub">
                        Kunder: {vendor.customers.slice(0, 5).join(", ")}
                      </span>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section aria-label="Hvem bruger det">
            <h3>Hvem bruger det</h3>
            {problem.references.length === 0 ? (
              <p className="cell-sub">Ingen dokumenteret brug endnu.</p>
            ) : (
              <ul>
                {problem.references.slice(0, 6).map((reference) => (
                  <li key={`${reference.name}-${reference.how}`}>
                    <strong>{reference.name}</strong>{" "}
                    <span className="cell-sub">
                      {reference.source_url ? (
                        <a
                          href={reference.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {reference.how}
                        </a>
                      ) : (
                        reference.how
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section aria-label="Dokumenteret effekt">
            <h3>Dokumenteret effekt</h3>
            {problem.effects.length === 0 ? (
              <p className="cell-sub">Ingen dokumenteret effekt fundet.</p>
            ) : (
              <ul>
                {problem.effects.slice(0, 4).map((effect, index) => (
                  <li
                    key={`${effect.organization}-${index}`}
                    title={effect.excerpt ?? undefined}
                  >
                    <strong>{effect.organization}:</strong> {effect.effect}
                    <span className="cell-sub">
                      {effect.vendor_source ? "Leverandørens egne tal · " : ""}
                      {effect.source_url ? (
                        <a
                          href={effect.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {effect.source_name ?? "Kilde"}
                        </a>
                      ) : (
                        (effect.source_name ?? "")
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}

      <section
        className="signal-section signal-recommendation problem-next"
        aria-label="Næste skridt"
      >
        <h3 className="section-title">
          Næste skridt <span className="section-tag">Anbefaling</span>
        </h3>
        {problem.opportunities.length === 0 ? (
          <p className="cell-sub">
            Ingen mulighed oprettet endnu.{" "}
            <Link href="/opportunities">Opret eller se muligheder →</Link>
          </p>
        ) : (
          <ul>
            {problem.opportunities.map((opportunity) => (
              <li key={opportunity.id}>
                <Link href={`/opportunities/${opportunity.id}`}>
                  {opportunity.title}
                </Link>
                : {opportunity.recommended_next_action}{" "}
                <span className="cell-sub">
                  (
                  {opportunity.approved
                    ? "godkendt"
                    : "kandidat, ikke godkendt"}
                  )
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </article>
  );
}

export default async function MulighederPage() {
  let problems: ProblemOpportunity[] | null = null;
  let loadError: unknown = null;
  try {
    problems = (await getOpportunityMap()).problems;
  } catch (error) {
    problems = null;
    loadError = error;
  }

  if (problems === null) {
    return (
      <>
        <h1>Muligheder for OK Kundeservice</h1>
        <ApiErrorAlert error={loadError} />
      </>
    );
  }

  const withVendors = problems.filter((p) => p.vendors.length > 0).length;
  const references = new Set(
    problems.flatMap((p) => p.references.map((r) => r.name)),
  ).size;
  const effects = new Set(
    problems.flatMap((p) =>
      p.effects.map((e) => `${e.organization}|${e.effect}`),
    ),
  ).size;

  return (
    <>
      <section className="hero" aria-label="Introduktion">
        <p className="hero-eyebrow">OK Kundeservice</p>
        <h1>Hvor kan AI hjælpe os — og hvem har gjort det før?</h1>
        <p className="hero-sub">
          Fra kundecentrets egne udfordringer til teknologien, leverandørerne og
          dokumenterede erfaringer fra andre. Alt bygger på kilder, der kan
          åbnes; leverandørers egne tal er markeret.
        </p>
      </section>

      <div className="kpi-grid">
        <div className="kpi-card">
          <p className="kpi-value">{withVendors}</p>
          <p className="kpi-label">Udfordringer med leverandørtilbud</p>
          <p className="kpi-definition">
            af {problems.length} i OK&#8217;s problemliste
          </p>
        </div>
        <div className="kpi-card">
          <p className="kpi-value">{references}</p>
          <p className="kpi-label">Organisationer med dokumenteret brug</p>
          <p className="kpi-definition">Godkendte claims med kilde</p>
        </div>
        <div className="kpi-card">
          <p className="kpi-value">{effects}</p>
          <p className="kpi-label">Dokumenterede effekter</p>
          <p className="kpi-definition">
            Rapporteret af brugerne selv eller leverandøren
          </p>
        </div>
      </div>

      <p className="cell-sub">
        Sorteret efter, hvor meget dokumentation radaren har — ikke efter en
        samlet score. <Link href="/vendors">Hele leverandørlandskabet →</Link>
      </p>

      {problems.map((problem) => (
        <ProblemCard key={problem.problem_id} problem={problem} />
      ))}
    </>
  );
}
