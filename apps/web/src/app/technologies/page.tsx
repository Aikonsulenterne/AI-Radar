import Link from "next/link";
import { listTechnologies, type Technology } from "../lib/api";

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
  try {
    technologies = (await listTechnologies()).items;
  } catch {
    technologies = null;
  }

  if (technologies === null) {
    return (
      <>
        <h1>Teknologiradar</h1>
        <div className="alert-error" role="alert">
          API&#8217;et kunne ikke nås. Start backenden og genindlæs siden.
        </div>
      </>
    );
  }

  return (
    <>
      <h1>Teknologiradar</h1>
      <p className="page-lead">
        Kuraterede AI-capabilities i tre horisonter. Adoption tælles kun på
        godkendte claims — der er ingen samlet score.
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
    </>
  );
}
