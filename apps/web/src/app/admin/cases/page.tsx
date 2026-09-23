import Link from "next/link";
import {
  listApprovedClaims,
  listCases,
  listCompanies,
  type AdoptionCase,
  type Claim,
  type Company,
} from "../../lib/api";
import { formatDateTime } from "../../lib/labels";
import { CaseRowActions, CreateCaseForm } from "./CaseBuilder";
import { ApiErrorAlert } from "../../../components/states/api-error";

export const dynamic = "force-dynamic";

const STATUS_LABELS: Record<AdoptionCase["status"], string> = {
  draft: "Kladde",
  published: "Publiceret",
  archived: "Arkiveret",
};

export default async function AdminCasesPage() {
  let cases: AdoptionCase[] | null = null;
  let loadError: unknown = null;
  let companies: Company[] = [];
  let approvedClaims: Claim[] = [];
  try {
    const [casePage, companyPage, claimPage] = await Promise.all([
      listCases(),
      listCompanies(),
      listApprovedClaims(),
    ]);
    cases = casePage.items;
    companies = companyPage.items;
    approvedClaims = claimPage.items;
  } catch (error) {
    cases = null;
    loadError = error;
  }

  return (
    <>
      <h1>Adoption cases</h1>
      <p className="page-lead">
        Saml en virksomheds godkendte claims til en publicerbar case. Fakta
        ligger i claims — casen er en præsentationsenhed.
      </p>

      {cases === null ? (
        <ApiErrorAlert error={loadError} requiredRole="Reviewer eller Admin" />
      ) : (
        <>
          <CreateCaseForm companies={companies} approvedClaims={approvedClaims} />

          {cases.length === 0 ? (
            <div className="empty-state">
              <p>
                <strong>Ingen cases endnu.</strong>
              </p>
              <p>Opret det første udkast ovenfor.</p>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Titel</th>
                  <th scope="col">Virksomhed</th>
                  <th scope="col">Status</th>
                  <th scope="col">Claims</th>
                  <th scope="col">Opdateret</th>
                  <th scope="col">Handlinger</th>
                </tr>
              </thead>
              <tbody>
                {cases.map((adoptionCase) => (
                  <tr key={adoptionCase.id}>
                    <td>
                      <Link href={`/adoption/cases/${adoptionCase.id}`}>
                        {adoptionCase.title}
                      </Link>
                    </td>
                    <td>{adoptionCase.company_name ?? "–"}</td>
                    <td>
                      <span
                        className={
                          adoptionCase.status === "published"
                            ? "badge badge-ok"
                            : "badge badge-muted"
                        }
                      >
                        {STATUS_LABELS[adoptionCase.status]}
                      </span>
                    </td>
                    <td>{adoptionCase.claim_count}</td>
                    <td>{formatDateTime(adoptionCase.updated_at)}</td>
                    <td>
                      <CaseRowActions adoptionCase={adoptionCase} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </>
  );
}
