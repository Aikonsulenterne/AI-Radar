import { listTechnologies, type Technology } from "../../lib/api";
import { formatDateTime } from "../../lib/labels";
import { ApiErrorAlert } from "../../../components/states/api-error";
import { CandidateActions } from "./CandidateActions";

export const dynamic = "force-dynamic";

export default async function AdminTechnologiesPage() {
  let technologies: Technology[] | null = null;
  let loadError: unknown = null;
  try {
    technologies = (await listTechnologies()).items;
  } catch (error) {
    technologies = null;
    loadError = error;
  }

  if (technologies === null) {
    return (
      <>
        <h1>Teknologier</h1>
        <ApiErrorAlert error={loadError} requiredRole="Reviewer eller Admin" />
      </>
    );
  }

  const candidates = technologies
    .filter((t) => t.is_candidate)
    .sort((a, b) =>
      (b.discovered_at ?? "").localeCompare(a.discovered_at ?? ""),
    );

  return (
    <>
      <h1>Teknologier</h1>
      <p className="page-lead">
        Nye capabilities, som radaren har fundet i markedet. Optag en kandidat
        på radaren ved at give den en horisont og en definition, eller afvis
        den. Kræver Admin; hver beslutning skrives til audit-loggen.
      </p>
      {candidates.length === 0 ? (
        <div className="empty-state">
          <p>
            <strong>Ingen kandidater at kuratere.</strong>
          </p>
          <p>Nye capabilities dukker op her efter kørsler.</p>
        </div>
      ) : (
        <div className="signal-list">
          {candidates.map((technology) => (
            <article key={technology.id} className="vendor-card">
              <h2 className="vendor-name">{technology.name}</h2>
              <p className="cell-sub">
                Fundet {formatDateTime(technology.discovered_at)} ·{" "}
                {technology.vendor_count} leverandør(er) ·{" "}
                {technology.adopting_company_count} virksomhed(er) med
                dokumenteret adoption
              </p>
              <CandidateActions technology={technology} />
            </article>
          ))}
        </div>
      )}
    </>
  );
}
