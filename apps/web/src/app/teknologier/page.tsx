import Link from "next/link";
import {
  getMarketTechnologies,
  type MarketArea,
  type MarketTechnology,
  type MarketVendorRow,
  type TechStatus,
} from "../lib/api";
import { ApiErrorAlert } from "../../components/states/api-error";
import { AREA_TABS, FilterTabs } from "../../components/market/area-tabs";
import { StatusBadge } from "../../components/market/status-badge";

export const dynamic = "force-dynamic";

const AREAS: MarketArea[] = ["salg", "kundeservice", "support"];
const AREA_LABELS: Record<string, string> = {
  salg: "Salg",
  kundeservice: "Kundeservice",
  support: "Support",
};
const SECTIONS: { status: TechStatus; title: string; intro: string }[] = [
  {
    status: "klar_nu",
    title: "Klar nu",
    intro: "Mindst to cases i drift og mindst én uafhængig kilde.",
  },
  {
    status: "vaerd_at_afproeve",
    title: "Værd at afprøve",
    intro: "Der findes cases, men kun i pilot eller med leverandørens egne tal.",
  },
  {
    status: "hold_oeje",
    title: "Hold øje med",
    intro: "På markedet, men endnu ingen cases.",
  },
];
const MAX_VENDORS = 3;

function TechnologyCard({ tech, showAreas }: { tech: MarketTechnology; showAreas: boolean }) {
  const offers = tech.vendors.filter((v) => !v.via_case);
  const named = (offers.length > 0 ? offers : tech.vendors).map((v) => v.name);
  const visible = named.slice(0, MAX_VENDORS);
  const more = named.length - visible.length;
  return (
    <article className="tech-card" id={`tech-${tech.id}`}>
      <header className="tech-card-head">
        <h3>{tech.label}</h3>
        <StatusBadge status={tech.status} label={tech.status_label} />
      </header>
      {showAreas ? (
        <p className="tech-areas">{tech.areas.map((a) => AREA_LABELS[a] ?? a).join(" · ")}</p>
      ) : null}
      {tech.what ? <p className="tech-what">{tech.what}</p> : null}
      {tech.for_ok ? (
        <div className="box-analysis">
          <span className="box-label">Det kan betyde for OK</span>
          <p>{tech.for_ok}</p>
        </div>
      ) : null}
      <div className="tech-vendors">
        <span className="box-label">Leverandører</span>
        <p>
          {visible.length > 0 ? visible.join(", ") : "Ikke oplyst"}
          {more > 0 ? <span className="muted"> + {more} flere</span> : null}
        </p>
      </div>
      <div className="tech-proof">
        {tech.best_case ? (
          <p>
            {tech.best_case.company}: {tech.best_case.text}{" "}
            <span className="muted small">· {tech.best_case.kind_label}</span>
          </p>
        ) : (
          <p className="muted">Ingen cases endnu</p>
        )}
      </div>
      {tech.vendors.length > 0 ? (
        <details className="tech-more">
          <summary>Vis leverandører og kilder</summary>
          <ul>
            {tech.vendors.map((v) => (
              <li key={v.company_id ?? v.name}>
                <strong>{v.name}</strong>
                {v.product ? <span className="muted">{v.product}</span> : null}
                {v.danish_supported ? <span className="dk-mark">✓ Dansk</span> : null}
                {v.via_case ? <span className="muted small">fra kundecase</span> : null}
                {v.source?.url ? (
                  <a href={v.source.url} target="_blank" rel="noreferrer">
                    Kilde
                  </a>
                ) : null}
              </li>
            ))}
          </ul>
        </details>
      ) : null}
      {tech.failed_case_count > 0 ? (
        <p className="tech-warning">
          <span aria-hidden="true">✕</span>{" "}
          <Link href={`/cases?teknologi=${tech.id}#fejl`}>
            {tech.failed_case_count === 1
              ? "1 case, hvor det ikke virkede – lær af den"
              : `${tech.failed_case_count} cases, hvor det ikke virkede – lær af dem`}
          </Link>
        </p>
      ) : null}
      <footer className="tech-foot">
        {tech.case_count > 0 ? (
          <Link href={`/cases?teknologi=${tech.id}`}>
            {tech.case_count === 1 ? "1 case – se den →" : `${tech.case_count} cases – se dem →`}
          </Link>
        ) : (
          <span className="muted">Ingen cases fundet endnu</span>
        )}
      </footer>
    </article>
  );
}

function VendorTable({ rows }: { rows: MarketVendorRow[] }) {
  return (
    <div className="table-card">
      <table className="v2-table">
        <thead>
          <tr>
            <th scope="col">Leverandør</th>
            <th scope="col">Type</th>
            <th scope="col">Teknologier</th>
            <th scope="col">Dansk</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((v) => (
            <tr key={v.name}>
              <th scope="row">
                {v.name}
                {v.ok_vendor ? <span className="ok-vendor">OK bruger i dag</span> : null}
              </th>
              <td className="muted">{v.type}</td>
              <td>
                <span className="pill-list">
                  {v.technologies.map((t) => (
                    <span key={t} className="pill">
                      {t}
                    </span>
                  ))}
                </span>
              </td>
              <td className={v.danish ? "dk-yes" : "muted"}>{v.danish ? "✓ Ja" : "Ikke oplyst"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default async function TechnologiesPage({
  searchParams,
}: {
  searchParams: Promise<{ omraade?: string }>;
}) {
  const { omraade } = await searchParams;
  const area = AREAS.includes(omraade as MarketArea) ? (omraade as MarketArea) : undefined;

  let data: Awaited<ReturnType<typeof getMarketTechnologies>> | null = null;
  let loadError: unknown = null;
  try {
    data = await getMarketTechnologies(area);
  } catch (error) {
    loadError = error;
  }

  const found = (data?.items ?? []).filter((t) => t.vendors.length > 0 || t.case_count > 0);
  const missing = (data?.items ?? []).filter(
    (t) => !t.is_new && t.vendors.length === 0 && t.case_count === 0,
  );

  return (
    <div className="market-v2">
      <div className="page-intro">
        <p className="eyebrow">Teknologier</p>
        <h1>Hvilke AI-teknologier findes der på markedet – og hvem sælger dem?</h1>
        <p>Det nyeste først. Derefter alle teknologier og de leverandører, der tilbyder dem.</p>
      </div>

      <FilterTabs
        label="Område"
        param="omraade"
        tabs={AREA_TABS}
        current={area}
        basePath="/teknologier"
        params={{}}
      />

      {data === null ? (
        <ApiErrorAlert error={loadError} />
      ) : (
        <>
          <nav className="jump-nav" aria-label="Indhold på siden">
            {data.new_on_market.length > 0 ? (
              <a href="#new-title">Nyt på markedet ({data.new_on_market.length})</a>
            ) : null}
            {SECTIONS.map((section) => {
              const n = found.filter((t) => t.status === section.status).length;
              return n > 0 ? (
                <a key={section.status} href={`#s-${section.status}`}>
                  {section.title} ({n})
                </a>
              ) : null;
            })}
            {data.vendors.length > 0 ? (
              <a href="#vendors-title">Leverandører på markedet ({data.vendors.length})</a>
            ) : null}
          </nav>

          {data.new_on_market.length > 0 ? (
            <section className="v2-section" aria-labelledby="new-title">
              <div className="v2-section-head">
                <h2 id="new-title">Nyt på markedet</h2>
                <span className="muted">Lanceret, annonceret eller fundet de seneste 90 dage</span>
              </div>
              <div className="card-grid-v2">
                {data.new_on_market.map(({ technology: t, why, date_label }) => {
                  const vendors = t.vendors.filter((v) => !v.via_case).slice(0, 3);
                  const source = t.vendors.find((v) => v.source?.url)?.source;
                  return (
                    <article key={t.id} className="tech-card tech-card-new">
                      <div className="new-meta">
                        <span className="new-pill">Nyt</span>
                        <span className="muted small">{date_label}</span>
                      </div>
                      <h3>{t.label}</h3>
                      {t.what ? <p className="tech-what">{t.what}</p> : null}
                      {why ? (
                        <div className="box-analysis">
                          <span className="box-label">Hvorfor værd at kende</span>
                          <p>{why}</p>
                        </div>
                      ) : null}
                      <div className="tech-foot">
                        <span className="pill-list">
                          {vendors.map((v) => (
                            <span key={v.name} className="pill pill-strong">
                              {v.name}
                            </span>
                          ))}
                        </span>
                        {source?.url ? (
                          <a href={source.url} target="_blank" rel="noreferrer">
                            Kilde →
                          </a>
                        ) : null}
                      </div>
                    </article>
                  );
                })}
              </div>
              <p className="ai-note">AI-sammenfattet · tjek kilden</p>
            </section>
          ) : null}

          {SECTIONS.map((section) => {
            const cards = found.filter((t) => t.status === section.status);
            if (cards.length === 0) return null;
            return (
              <section
                key={section.status}
                className="v2-section"
                aria-labelledby={`s-${section.status}`}
              >
                <div className="v2-section-head">
                  <h2 id={`s-${section.status}`}>{section.title}</h2>
                  <span className="muted">{section.intro}</span>
                </div>
                <div className="card-grid-v2">
                  {cards.map((t) => (
                    <TechnologyCard key={t.id} tech={t} showAreas={area === undefined} />
                  ))}
                </div>
                <p className="ai-note">AI-sammenfattet · tjek kilden</p>
              </section>
            );
          })}

          {missing.length > 0 ? (
            <p className="empty-line">
              Ikke fundet i kilderne endnu: {missing.map((t) => t.label).join(" · ")}
            </p>
          ) : null}

          {data.vendors.length > 0 ? (
            <section className="v2-section" aria-labelledby="vendors-title">
              <div className="v2-section-head">
                <h2 id="vendors-title">Leverandører på markedet</h2>
                <span className="muted">
                  Hvem tilbyder hvad · ✓ Ja = kilden siger, at løsningen understøtter dansk
                </span>
              </div>
              <VendorTable rows={data.vendors} />
            </section>
          ) : null}
        </>
      )}
    </div>
  );
}
