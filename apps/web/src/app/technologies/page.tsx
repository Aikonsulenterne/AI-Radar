import Link from "next/link";
import { listTechnologies, type Technology } from "../lib/api";
import { ApiErrorAlert } from "../../components/states/api-error";
import { formatDateTime } from "../lib/labels";

export const dynamic = "force-dynamic";

const HORIZONS: {
  key: Technology["horizon"];
  title: string;
  description: string;
}[] = [
  {
    key: "now",
    title: "NU",
    description: "Relativt modent og anvendeligt i dag",
  },
  {
    key: "next",
    title: "NÆSTE",
    description: "Bør undersøges i den nærmeste planlægningshorisont",
  },
  {
    key: "horizon",
    title: "HORIZON",
    description: "Kan få væsentlig betydning inden for 1–3 år; højere usikkerhed",
  },
];

export default async function TechnologiesPage() {
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
        <h1>Teknologiradar</h1>
        <ApiErrorAlert error={loadError} />
      </>
    );
  }

  return (
    <>
      <h1>Teknologiradar</h1>
      <p className="page-lead">
        Kuraterede AI-capabilities til kundecentre i tre horisonter.
        Leverandørtilbud og adoption tælles kun på godkendte claims — der er
        ingen samlet score. <Link href="/vendors">Se leverandørerne →</Link>
      </p>

      {technologies.length === 0 ? (
        <div className="empty-state">
          <p>
            <strong>Ingen teknologier endnu.</strong>
          </p>
          <p>Startteknologierne indlæses via seed-data (supabase/seed.sql).</p>
        </div>
      ) : (
        <div className="horizon-grid">
          {HORIZONS.map((horizon) => (
            <section
              key={horizon.key}
              aria-label={horizon.title}
              className={
                horizon.key === "horizon"
                  ? "horizon-col horizon-col-dark"
                  : "horizon-col horizon-col-light"
              }
            >
              <h2 className="section-title">{horizon.title}</h2>
              <p className="cell-sub">{horizon.description}</p>
              <div className="signal-list">
                {technologies
                  .filter((t) => t.horizon === horizon.key)
                  .map((technology) => (
                    <Link
                      key={technology.id}
                      href={`/technologies/${technology.id}`}
                      className="signal-card-link"
                    >
                      <article className="signal-card">
                        <h3 className="signal-title">{technology.name}</h3>
                        <p className="signal-summary">
                          {technology.definition}
                        </p>
                        <p className="cell-sub">
                          {technology.vendor_count} leverandør(er) med
                          dokumenteret tilbud ·{" "}
                          {technology.adopting_company_count} virksomhed(er)
                          med dokumenteret adoption
                        </p>
                      </article>
                    </Link>
                  ))}
              </div>
            </section>
          ))}
        </div>
      )}

      <NewInMarket
        candidates={technologies
          .filter((t) => t.is_candidate)
          .sort((a, b) =>
            (b.discovered_at ?? "").localeCompare(a.discovered_at ?? ""),
          )}
      />
    </>
  );
}

/** Capabilities fundet i markedet, som radaren ikke kendte — ikke kurateret. */
function NewInMarket({ candidates }: { candidates: Technology[] }) {
  return (
    <section aria-label="Nyt i markedet" className="landscape-capability">
      <h2 className="section-title">
        Nyt i markedet{" "}
        <span className="section-tag">Fundet automatisk · ikke kurateret</span>
      </h2>
      <p className="page-lead">
        Capabilities, som leverandører tilbyder eller organisationer bruger, men
        som ikke står på radaren endnu. En administrator placerer dem i en
        horisont eller afviser dem under Admin → Teknologier.
      </p>
      {candidates.length === 0 ? (
        <p className="cell-sub">Ingen nye capabilities fundet endnu.</p>
      ) : (
        <div className="vendor-grid">
          {candidates.map((technology) => (
            <Link
              key={technology.id}
              href={`/technologies/${technology.id}`}
              className="signal-card-link"
            >
              <article className="signal-card">
                <h3 className="signal-title">{technology.name}</h3>
                <p className="cell-sub">
                  Fundet {formatDateTime(technology.discovered_at)} ·{" "}
                  {technology.vendor_count} leverandør(er) ·{" "}
                  {technology.adopting_company_count} virksomhed(er) med
                  dokumenteret adoption
                </p>
              </article>
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}
