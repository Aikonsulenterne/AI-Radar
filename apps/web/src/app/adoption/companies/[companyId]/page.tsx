import Link from "next/link";
import { getCompany, type CompanyDetail } from "../../../lib/api";

export const dynamic = "force-dynamic";

export default async function CompanyPage({
  params,
}: {
  params: Promise<{ companyId: string }>;
}) {
  const { companyId } = await params;
  let company: CompanyDetail | null = null;
  try {
    company = await getCompany(companyId);
  } catch {
    company = null;
  }

  if (company === null) {
    return (
      <>
        <h1>Virksomhed</h1>
        <div className="alert-error" role="alert">
          Virksomheden kunne ikke hentes.
        </div>
        <p>
          <Link href="/adoption">Tilbage til AI-adoption</Link>
        </p>
      </>
    );
  }

  return (
    <>
      <p className="cell-sub">
        <Link href="/adoption">← AI-adoption</Link>
      </p>
      <h1>{company.name}</h1>
      <p className="page-lead">
        Land: {company.country_code ?? "Ikke dokumenteret"} · Branche:{" "}
        {company.industry ?? "Ikke dokumenteret"} ·{" "}
        {company.approved_claim_count} godkendte claims
      </p>

      {company.cases.length > 0 ? (
        <section className="signal-section" aria-label="Cases">
          <h2 className="section-title">Publicerede cases</h2>
          <ul>
            {company.cases.map((adoptionCase) => (
              <li key={adoptionCase.id}>
                <Link href={`/adoption/cases/${adoptionCase.id}`}>
                  {adoptionCase.title}
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section
        className="signal-section section-fact"
        aria-label="Dokumenterede claims"
      >
        <h2 className="section-title">
          Dokumenterede claims{" "}
          <span className="section-tag">Dokumenteret fakta</span>
        </h2>
        {company.claims.length === 0 ? (
          <p className="cell-sub">Ingen godkendte claims endnu.</p>
        ) : (
          <div className="claim-list">
            {company.claims.map((claim) => (
              <article className="claim-card" key={claim.id}>
                <p className="claim-statement">
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
    </>
  );
}
