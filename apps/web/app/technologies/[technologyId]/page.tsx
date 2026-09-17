import Link from "next/link";
import { getTechnology, type TechnologyDetail } from "../../lib/api";

export const dynamic = "force-dynamic";

const HORIZON_LABELS: Record<TechnologyDetail["horizon"], string> = {
  now: "NU",
  next: "NÆSTE",
  horizon: "HORIZON",
};

export default async function TechnologyPage({
  params,
}: {
  params: Promise<{ technologyId: string }>;
}) {
  const { technologyId } = await params;
  let technology: TechnologyDetail | null = null;
  try {
    technology = await getTechnology(technologyId);
  } catch {
    technology = null;
  }

  if (technology === null) {
    return (
      <>
        <h1>Teknologi</h1>
        <div className="alert-error" role="alert">
          Teknologien kunne ikke hentes.
        </div>
        <p>
          <Link href="/technologies">Tilbage til Teknologiradar</Link>
        </p>
      </>
    );
  }

  return (
    <>
      <p className="cell-sub">
        <Link href="/technologies">← Teknologiradar</Link>
      </p>
      <h1>{technology.name}</h1>
      <p className="page-lead">
        <span className="badge badge-muted">
          {HORIZON_LABELS[technology.horizon]}
        </span>{" "}
        {technology.definition}
      </p>

      <section className="signal-section" aria-label="Dokumenteret adoption">
        <h2 className="section-title">
          Skandinavisk adoption{" "}
          <span className="section-tag">Kun godkendte claims</span>
        </h2>
        {technology.companies.length === 0 ? (
          <p className="cell-sub">
            Ingen dokumenteret adoption endnu. Momentum og modenhed vurderes
            ikke uden evidens.
          </p>
        ) : (
          <ul>
            {technology.companies.map((company) => (
              <li key={company.id}>
                <Link href={`/adoption/companies/${company.id}`}>
                  {company.name}
                </Link>{" "}
                <span className="cell-sub">
                  ({company.approved_claim_count} godkendte claims)
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {technology.claims.length > 0 ? (
        <section className="signal-section" aria-label="Evidens">
          <h2 className="section-title">
            Evidens <span className="section-tag">Uddrag fra kilder</span>
          </h2>
          <div className="claim-list">
            {technology.claims.map((claim) => (
              <article className="claim-card" key={claim.id}>
                <p className="claim-statement">
                  <b>{claim.subject_name ?? "(ukendt)"}</b>{" "}
                  <span className="claim-predicate">{claim.predicate}</span>{" "}
                  {technology.name}
                </p>
                {claim.evidence.map((evidence) => (
                  <blockquote className="evidence-quote" key={evidence.id}>
                    &#8220;{evidence.supporting_excerpt}&#8221;
                  </blockquote>
                ))}
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </>
  );
}
