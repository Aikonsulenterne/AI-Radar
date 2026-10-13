import {
  getMarketCases,
  type MarketArea,
  type MarketCase,
  type MarketRegion,
  type MarketTechnologyRef,
} from "../lib/api";
import { getRole } from "../lib/me";
import { ApiErrorAlert } from "../../components/states/api-error";
import { AREA_TABS, FilterTabs } from "../../components/market/area-tabs";
import { CaseCard } from "../../components/market/case-card";
import { TechnologySelect } from "../../components/market/technology-select";

export const dynamic = "force-dynamic";

const AREAS: MarketArea[] = ["salg", "kundeservice", "support"];
const REGIONS: MarketRegion[] = ["danmark", "norden", "verden"];
const REGION_TABS = [
  { value: undefined, label: "Hele verden" },
  { value: "danmark", label: "Danmark" },
  { value: "norden", label: "Norden" },
  { value: "verden", label: "Resten af verden" },
];

export default async function CasesPage({
  searchParams,
}: {
  searchParams: Promise<{ omraade?: string; region?: string; teknologi?: string }>;
}) {
  const params = await searchParams;
  const area = AREAS.includes(params.omraade as MarketArea)
    ? (params.omraade as MarketArea)
    : undefined;
  const region = REGIONS.includes(params.region as MarketRegion)
    ? (params.region as MarketRegion)
    : undefined;
  const technology = params.teknologi || undefined;

  let items: MarketCase[] | null = null;
  let technologies: MarketTechnologyRef[] = [];
  let loadError: unknown = null;
  const [result, role] = await Promise.all([
    getMarketCases({ area, region, technology_id: technology }).then(
      (value) => ({ value }),
      (error: unknown) => ({ error }),
    ),
    getRole(),
  ]);
  if ("value" in result) {
    items = result.value.items;
    technologies = result.value.technologies;
  } else loadError = result.error;
  const isAdmin = role === "admin";
  const current = { omraade: area, region, teknologi: technology };

  return (
    <>
      <h1>Sådan gør andre</h1>
      <p className="page-lead">
        Hvordan andre virksomheder bruger AI i salg, kundeservice og support — og
        hvad det har givet. Danske og nordiske cases og cases med dokumenteret
        effekt står først.
      </p>

      <div className="filter-row">
        <FilterTabs
          label="Område"
          param="omraade"
          tabs={AREA_TABS}
          current={area}
          basePath="/cases"
          params={current}
        />
        <FilterTabs
          label="Region"
          param="region"
          tabs={REGION_TABS}
          current={region}
          basePath="/cases"
          params={current}
        />
        <TechnologySelect options={technologies} current={technology} />
      </div>

      {items === null ? (
        <ApiErrorAlert error={loadError} />
      ) : items.length === 0 ? (
        <div className="empty-state">
          <p>
            <strong>Ingen cases med de valgte filtre.</strong>
          </p>
          <p>Prøv et andet område eller en anden region.</p>
        </div>
      ) : (
        <>
          <p className="cell-sub">
            {items.length === 1 ? "1 case" : `${items.length} cases`}
          </p>
          <div className="market-grid">
            {items.map((item) => (
              <CaseCard key={item.id} item={item} isAdmin={isAdmin} />
            ))}
          </div>
        </>
      )}
    </>
  );
}
