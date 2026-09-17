import Link from "next/link";
import { getCase, type AdoptionCaseDetail } from "../../../lib/api";

export const dynamic = "force-dynamic";

function FactRow({ label, value }: { label: string; value: string | null }) {
  return (
    <tr>
      <th scope="row">{label}</th>
      <td>{value ?? "Ikke dokumenteret"}</td>
    </tr>
  );
}

export default async function CasePage({
  params,
}: {
  params: Promise<{ caseId: string }>;
}) {
  const { caseId } = await params;
  let adoptionCase: AdoptionCaseDetail | null = null;
  try {
    adoptionCase = await getCase(caseId);
  } catch {
    adoptionCase = null;
  }

  if (adoptionCase === null) {
    return (
      <>
        <h1>Adoption case</h1>
        <div className="alert-error" role="alert">
          Casen kunne ikke hentes — den findes ikke, er ikke publiceret, eller
          API&#8217;et kører ikke.
        </div>
        <p>
          <Link href="/adoption">Tilbage til AI-adoption</Link>
        </p>
      </>
    );
  }

  const facts = adoptionCase.facts;

  return (
    <>
      <p className="cell-sub">
        <Link href="/adoption">← AI-adoption</Link>
      </p>
      <h1>{adoptionCase.title}</h1>
      <p className="page-lead">
        {adoptionCase.company_name ? (
          <Link href={`/adoption/companies/${adoptionCase.company_id}`}>
            {adoptionCase.company_name}
          </Link>
        ) : (
          "Ukendt virksomhed"
        )}{" "}
        · {adoptionCase.claim_count} godkendte claims som faktagrundlag
      </p>

      <section
        className="signal-section section-fact"
        aria-label="Dokumenterede fakta"
      >
        <h2 className="section-title">
          Fakta <span className="section-tag">Dokumenteret fakta</span>
        </h2>
        <table className="data-table facts-table">
          <tbody>
            <FactRow label="Capability" value={facts.capability} />
            <FactRow label="Use case" value={facts.use_case} />
            <FactRow label="Implementeringsstadie" value={facts.stage} />
            <FactRow label="Leverandør/platform" value={facts.vendor} />
            <tr>
              <th scope="row">Dokumenteret effekt</th>
              <td>{facts.effect ?? "Ingen dokumenteret effekt fundet"}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section className="signal-section section-fact" aria-label="Evidens">
        <h2 className="section-title">
          Evidens <span className="section-tag">Uddrag fra kilder</span>
        </h2>
        <div className="claim-list">
          {adoptionCase.claims.map((claim) => (
            <article className="claim-card" key={claim.id}>
              <p className="claim-statement">
                <span className="claim-predicate">{claim.predicate}</span>{" "}
                {claim.object_name ?? claim.object_text ?? (
                  <i>Ikke dokumenteret</i>
                )}{" "}
                <span className="cell-sub">
                  Reviewstatus: {claim.review_status}
                </span>
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
      </section>

      {adoptionCase.summary ? (
        <section className="signal-section signal-analysis" aria-label="Analyse">
          <h2 className="section-title">
            Potentiel læring{" "}
            <span className="section-tag">Analyse, ikke fakta</span>
          </h2>
          <p>{adoptionCase.summary}</p>
        </section>
      ) : null}

      {adoptionCase.technologies.length > 0 ? (
        <p className="cell-sub">
          Relaterede teknologier: {adoptionCase.technologies.join(", ")}
        </p>
      ) : null}
    </>
  );
}
