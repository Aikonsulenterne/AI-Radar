import Link from "next/link";
import {
  listCases,
  listCompanies,
  type AdoptionCase,
  type Company,
} from "../lib/api";
import { ApiErrorAlert } from "../../components/states/api-error";

export const dynamic = "force-dynamic";

function factLine(facts: AdoptionCase["facts"]): string {
  const parts: string[] = [];
  if (facts.capability) parts.push(facts.capability);
  if (facts.use_case) parts.push(`til ${facts.use_case}`);
  parts.push(facts.stage ? `Stadie: ${facts.stage}` : "Stadie: Ikke dokumenteret");
  return parts.join(" · ");
}

export default async function AdoptionPage() {
  let cases: AdoptionCase[] | null = null;
  let loadError: unknown = null;
  let companies: Company[] = [];
  try {
    const [casePage, companyPage] = await Promise.all([
      listCases(),
      listCompanies(),
    ]);
    cases = casePage.items;
    companies = companyPage.items;
  } catch (error) {
    cases = null;
    loadError = error;
  }

  if (cases === null) {
    return (
      <>
        <h1>AI-adoption</h1>
        <ApiErrorAlert error={loadError} />
      </>
    );
  }

  return (
    <>
      <h1>AI-adoption</h1>
      <p className="page-lead">
        Dokumenterede cases og virksomheder. Manglende fakta vises som
        &#8220;Ikke dokumenteret&#8221; og gættes aldrig.
      </p>

      <h2 className="section-title">Publicerede cases</h2>
      {cases.length === 0 ? (
        <div className="empty-state">
          <p>
            <strong>Ingen publicerede cases endnu.</strong>
          </p>
          <p>Cases samles af godkendte claims og publiceres af en reviewer.</p>
        </div>
      ) : (
        <div className="signal-list">
          {cases.map((adoptionCase) => (
            <Link
              key={adoptionCase.id}
              href={`/adoption/cases/${adoptionCase.id}`}
              className="signal-card-link"
            >
              <article className="signal-card">
                <header className="claim-card-header">
                  <span className="badge badge-muted">
                    {adoptionCase.company_name ?? "Ukendt virksomhed"}
                  </span>
                  <span className="cell-sub">
                    {adoptionCase.claim_count} godkendte claims
                  </span>
                </header>
                <h3 className="signal-title">{adoptionCase.title}</h3>
                <p className="signal-summary">{factLine(adoptionCase.facts)}</p>
              </article>
            </Link>
          ))}
        </div>
      )}

      <h2 className="section-title">Virksomheder</h2>
      {companies.length === 0 ? (
        <div className="empty-state">
          <p>
            <strong>Ingen virksomheder endnu.</strong>
          </p>
          <p>
            Virksomheder oprettes automatisk, når claims udtrækkes og
            godkendes.
          </p>
        </div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">Virksomhed</th>
              <th scope="col">Land</th>
              <th scope="col">Branche</th>
              <th scope="col">Godkendte claims</th>
              <th scope="col">Cases</th>
            </tr>
          </thead>
          <tbody>
            {companies.map((company) => (
              <tr key={company.id}>
                <td>
                  <Link href={`/adoption/companies/${company.id}`}>
                    {company.name}
                  </Link>
                </td>
                <td>{company.country_code ?? "Ikke dokumenteret"}</td>
                <td>{company.industry ?? "Ikke dokumenteret"}</td>
                <td>{company.approved_claim_count}</td>
                <td>{company.published_case_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
