import Link from "next/link";
import { getCompany, type CompanyDetail } from "../../../lib/api";
import { ApiErrorAlert } from "../../../../components/states/api-error";
import { FactGroups } from "../../../../components/facts/fact-groups";

export const dynamic = "force-dynamic";

export default async function CompanyPage({
  params,
}: {
  params: Promise<{ companyId: string }>;
}) {
  const { companyId } = await params;
  let company: CompanyDetail | null = null;
  let loadError: unknown = null;
  try {
    company = await getCompany(companyId);
  } catch (error) {
    company = null;
    loadError = error;
  }

  if (company === null) {
    return (
      <>
        <h1>Virksomhed</h1>
        <ApiErrorAlert error={loadError} notFound="Virksomheden findes ikke." />
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
        <FactGroups
          claims={company.claims}
          showSubject={false}
          empty="Ingen godkendte claims endnu."
        />
      </section>
    </>
  );
}
