import Link from "next/link";
import {
  getMarketTechnologies,
  type MarketArea,
  type MarketTechnology,
} from "../lib/api";
import { getRole } from "../lib/me";
import { ApiErrorAlert } from "../../components/states/api-error";
import { AREA_TABS, FilterTabs } from "../../components/market/area-tabs";
import { AiNote } from "../../components/market/ai-note";
import { HideButton } from "../../components/market/hide-button";

export const dynamic = "force-dynamic";

const AREAS: MarketArea[] = ["salg", "kundeservice", "support"];
const AREA_LABELS: Record<string, string> = {
  salg: "Salg",
  kundeservice: "Kundeservice",
  support: "Support",
};

function TechnologyCard({ tech, isAdmin }: { tech: MarketTechnology; isAdmin: boolean }) {
  const offers = tech.vendors.filter((v) => !v.via_case);
  const fromCases = tech.vendors.filter((v) => v.via_case);
  return (
    <article className="market-card" id={`tech-${tech.id}`}>
      <header className="market-card-head">
        <h3 className="market-card-title">{tech.label}</h3>
        <span className="area-badges">
          {tech.is_new ? <span className="badge badge-candidate">Nyt i markedet</span> : null}
          {tech.areas.map((area) => (
            <span key={area} className="badge badge-muted">
              {AREA_LABELS[area] ?? area}
            </span>
          ))}
        </span>
      </header>
      {tech.what ? <p className="market-card-lead">{tech.what}</p> : null}
      {tech.value ? <p className="market-value">{tech.value}</p> : null}

      <h4 className="market-subhead">Leverandører</h4>
      {offers.length === 0 && fromCases.length === 0 ? (
        <p className="cell-sub">Ingen leverandører fundet i kilderne endnu.</p>
      ) : (
        <ul className="vendor-list">
          {offers.map((v) => (
            <li key={v.company_id ?? v.name}>
              <strong>{v.name}</strong>
              {v.product ? ` — ${v.product}` : ""}
              {v.danish_supported ? <span className="badge badge-ok">Dansk</span> : null}{" "}
              {v.source?.url ? (
                <a href={v.source.url} target="_blank" rel="noreferrer" className="inline-source">
                  kilde
                </a>
              ) : null}
              {isAdmin && v.item_ids.length > 0 ? <HideButton itemIds={v.item_ids} /> : null}
            </li>
          ))}
          {fromCases.length > 0 ? (
            <li className="cell-sub">
              Kendt fra kundecases: {fromCases.map((v) => v.name).join(", ")}
            </li>
          ) : null}
        </ul>
      )}

      <footer className="market-card-foot">
        {tech.case_count > 0 ? (
          <Link href={`/cases?teknologi=${tech.id}`}>
            {tech.case_count === 1 ? "1 case" : `${tech.case_count} cases`} →
          </Link>
        ) : (
          <span className="cell-sub">Ingen cases fundet endnu</span>
        )}
        <AiNote />
      </footer>
    </article>
  );
}

export default async function TechnologiesPage({
  searchParams,
}: {
  searchParams: Promise<{ omraade?: string }>;
}) {
  const { omraade } = await searchParams;
  const area = AREAS.includes(omraade as MarketArea) ? (omraade as MarketArea) : undefined;

  let items: MarketTechnology[] | null = null;
  let loadError: unknown = null;
  const [result, role] = await Promise.all([
    getMarketTechnologies(area).then(
      (value) => ({ value }),
      (error: unknown) => ({ error }),
    ),
    getRole(),
  ]);
  if ("value" in result) items = result.value.items;
  else loadError = result.error;
  const isAdmin = role === "admin";

  const found = (items ?? []).filter((t) => t.vendors.length > 0 || t.case_count > 0);
  const known = found.filter((t) => !t.is_new);
  const fresh = found.filter((t) => t.is_new);
  const missing = (items ?? []).filter((t) => !t.is_new && t.vendors.length === 0 && t.case_count === 0);

  return (
    <>
      <h1>Teknologier</h1>
      <p className="page-lead">
        Hvilken AI findes der på markedet til salg, kundeservice og support — og
        hvem sælger den.
      </p>
      <FilterTabs
        label="Område"
        param="omraade"
        tabs={AREA_TABS}
        current={area}
        basePath="/teknologier"
        params={{}}
      />

      {items === null ? (
        <ApiErrorAlert error={loadError} />
      ) : (
        <>
          {known.length === 0 && fresh.length === 0 ? (
            <div className="empty-state">
              <p>
                <strong>Ingen teknologier fundet i kilderne endnu.</strong>
              </p>
            </div>
          ) : (
            <div className="market-grid">
              {known.map((t) => (
                <TechnologyCard key={t.id} tech={t} isAdmin={isAdmin} />
              ))}
            </div>
          )}

          {fresh.length > 0 ? (
            <section aria-label="Nyt i markedet">
              <h2 className="section-title">Nyt i markedet</h2>
              <p className="cell-sub">
                Teknologier, radaren har fundet hos leverandører, og som ikke står på
                listen endnu.
              </p>
              <div className="market-grid">
                {fresh.map((t) => (
                  <TechnologyCard key={t.id} tech={t} isAdmin={isAdmin} />
                ))}
              </div>
            </section>
          ) : null}

          {missing.length > 0 ? (
            <p className="cell-sub brief-gaps">
              Ikke fundet i kilderne endnu: {missing.map((t) => t.label).join(" · ")}
            </p>
          ) : null}
        </>
      )}
    </>
  );
}
