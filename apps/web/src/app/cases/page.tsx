import {
  getMarketCases,
  type MarketCase,
  type MarketRegion,
  type MarketTechnologyRef,
} from "../lib/api";
import { ApiErrorAlert } from "../../components/states/api-error";
import { FilterTabs } from "../../components/market/area-tabs";
import { CaseCard } from "../../components/market/case-card";
import { TechnologySelect } from "../../components/market/technology-select";

export const dynamic = "force-dynamic";

const REGIONS: MarketRegion[] = ["danmark", "norden", "verden"];
// Norden omfatter Danmark (designhandoff v2 §6).
const REGION_TABS = [
  { value: undefined, label: "Alle" },
  { value: "danmark", label: "Danmark" },
  { value: "norden", label: "Norden" },
  { value: "verden", label: "Resten af verden" },
];

export default async function CasesPage({
  searchParams,
}: {
  searchParams: Promise<{ region?: string; teknologi?: string }>;
}) {
  const params = await searchParams;
  const region = REGIONS.includes(params.region as MarketRegion)
    ? (params.region as MarketRegion)
    : undefined;
  const technology = params.teknologi || undefined;

  let items: MarketCase[] | null = null;
  let technologies: MarketTechnologyRef[] = [];
  let counts = { all: 0, danish: 0 };
  let peersWithout: string[] = [];
  let loadError: unknown = null;
  try {
    const data = await getMarketCases({ region, technology_id: technology });
    items = data.items;
    technologies = data.technologies;
    counts = { all: data.all_total, danish: data.danish_total };
    peersWithout = data.peers_without_cases;
  } catch (error) {
    loadError = error;
  }

  const peers = (items ?? []).filter((item) => item.peer);
  const others = (items ?? []).filter((item) => !item.peer);

  return (
    <div className="market-v2">
      <div className="page-intro">
        <p className="eyebrow">Sådan gør andre</p>
        <h1>Hvordan bruger andre kundecentre AI?</h1>
        <p>
          Kun organisationer, der selv bruger AI. Effekt og læring står, som kilden
          skriver dem. Dem, der ligner OK, står øverst.
        </p>
      </div>

      <div className="filter-row">
        <FilterTabs
          label="Region"
          param="region"
          tabs={REGION_TABS}
          current={region}
          basePath="/cases"
          params={{ region, teknologi: technology }}
        />
        <TechnologySelect options={technologies} current={technology} />
        {items !== null ? (
          <span className="muted small">
            {items.length} af {counts.all} cases · {counts.danish} fra Danmark
          </span>
        ) : null}
      </div>

      {items === null ? (
        <ApiErrorAlert error={loadError} />
      ) : (
        <>
          {region !== "verden" ? (
            <section className="v2-section" aria-labelledby="peers-title">
              <div className="v2-section-head">
                <h2 id="peers-title">Dem, der ligner OK</h2>
                <span className="muted">
                  Danske selskaber inden for energi, brændstof og ladning, mobil og internet
                </span>
              </div>
              {peers.length > 0 ? (
                <div className="case-grid-v2">
                  {peers.map((item) => (
                    <CaseCard key={item.id} item={item} />
                  ))}
                </div>
              ) : (
                <p className="empty-line">Ingen AI-cases fra dem, der ligner OK, for dette valg endnu.</p>
              )}
              {peersWithout.length > 0 ? (
                <p className="muted small">
                  Ingen AI-case fundet endnu: {peersWithout.join(" · ")}
                </p>
              ) : null}
            </section>
          ) : null}

          <section className="v2-section" aria-label="Andre kundecentre">
            {region !== "verden" ? (
              <div className="v2-section-head">
                <h2>Andre kundecentre</h2>
              </div>
            ) : null}
            {others.length === 0 ? (
              <p className="empty-line">Ingen cases fundet for dette valg endnu.</p>
            ) : (
              <div className="case-grid-v2">
                {others.map((item) => (
                  <CaseCard key={item.id} item={item} />
                ))}
              </div>
            )}
          </section>
          <p className="ai-note">AI-sammenfattet · tjek kilden</p>
        </>
      )}
    </div>
  );
}
