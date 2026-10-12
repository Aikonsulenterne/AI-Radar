import Link from "next/link";
import { getCase, type AdoptionCaseDetail } from "../../../lib/api";
import { AiPublishedBadge } from "../../../../components/states/ai-badge";
import { ApiErrorAlert } from "../../../../components/states/api-error";
import { FactGroups } from "../../../../components/facts/fact-groups";

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
  let loadError: unknown = null;
  try {
    adoptionCase = await getCase(caseId);
  } catch (error) {
    adoptionCase = null;
    loadError = error;
  }

  if (adoptionCase === null) {
    return (
      <>
        <h1>Adoption case</h1>
        <ApiErrorAlert
          error={loadError}
          notFound="Casen findes ikke, er arkiveret eller er ikke publiceret endnu."
        />
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
        {adoptionCase.auto_published ? (
          <>
            <AiPublishedBadge />{" "}
          </>
        ) : null}
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
        <FactGroups claims={adoptionCase.claims} />
      </section>

      {adoptionCase.summary ? (
        <section
          className="signal-section signal-analysis"
          aria-label="Analyse"
        >
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
