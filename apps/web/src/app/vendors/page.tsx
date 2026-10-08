import Link from "next/link";
import {
  getVendorLandscape,
  type LandscapeCapability,
  type Offering,
  type VendorFact,
  type VendorLandscape,
} from "../lib/api";
import {
  SOURCE_TYPE_LABELS,
  formatDateTime,
  isVendorSource,
} from "../lib/labels";
import { ApiErrorAlert } from "../../components/states/api-error";
import { HorizonBadge } from "../../components/states/horizon-badge";

export const dynamic = "force-dynamic";


function anchorId(capability: LandscapeCapability): string {
  return `cap-${capability.technology?.slug ?? "oevrige"}`;
}

function OfferingItem({ offering }: { offering: Offering }) {
  const sourceLabel = offering.source_type
    ? (SOURCE_TYPE_LABELS[offering.source_type] ?? offering.source_type)
    : null;
  return (
    <li>
      <strong>{offering.product ?? "Produkt ikke navngivet"}</strong>
      <span className="cell-sub">
        {offering.source_name ?? "Ukendt kilde"}
        {sourceLabel ? ` · ${sourceLabel}` : ""}
        {offering.observed_at ? ` · ${formatDateTime(offering.observed_at)}` : ""}
        {offering.auto_approved ? " · Automatisk godkendt af AI" : ""}
      </span>
      {isVendorSource(offering.source_type) ? (
        <span className="cell-sub">Leverandørens eget udsagn</span>
      ) : null}
      {offering.also_reported_by.length > 0 ? (
        <span className="cell-sub">
          Også omtalt af: {offering.also_reported_by.join(", ")}
        </span>
      ) : null}
      {offering.excerpt ? (
        <p className="offering-excerpt">&ldquo;{offering.excerpt}&rdquo;</p>
      ) : null}
      {offering.source_url ? (
        <a href={offering.source_url} target="_blank" rel="noopener noreferrer">
          Original kilde ↗
        </a>
      ) : null}
    </li>
  );
}

function VendorFacts({ label, facts }: { label: string; facts: VendorFact[] }) {
  return (
    <p className="vendor-customers">
      <strong>{label}:</strong>{" "}
      {facts.length === 0 ? (
        <span className="cell-sub">Ikke dokumenteret</span>
      ) : (
        facts.map((fact, index) => (
          <span key={fact.value} title={fact.excerpt ?? undefined}>
            {index > 0 ? ", " : ""}
            {fact.source_url ? (
              <a href={fact.source_url} target="_blank" rel="noopener noreferrer">
                {fact.value}
              </a>
            ) : (
              fact.value
            )}
          </span>
        ))
      )}
    </p>
  );
}

function CapabilitySection({ capability }: { capability: LandscapeCapability }) {
  const technology = capability.technology;
  return (
    <section
      id={anchorId(capability)}
      className="landscape-capability"
      aria-label={capability.capability_name}
    >
      <div className="landscape-capability-head">
        <h2 className="section-title">
          {technology ? (
            <Link href={`/technologies/${technology.id}`}>
              {capability.capability_name}
            </Link>
          ) : (
            capability.capability_name
          )}
        </h2>
        {technology ? (
          <HorizonBadge technology={technology} />
        ) : null}
        <span className="cell-sub">
          {capability.vendors.length} leverandør(er)
          {technology
            ? ` · ${technology.adopting_company_count} virksomhed(er) med dokumenteret adoption`
            : ""}
        </span>
      </div>
      <p className="page-lead">
        {technology?.definition ??
          "Tilbud, hvis capability ikke findes på radarens kuraterede liste."}
      </p>
      <div className="vendor-grid">
        {capability.vendors.map((vendor) => (
          <article key={vendor.company_id} className="vendor-card">
            <h3 className="vendor-name">{vendor.name}</h3>
            <ul className="offering-list">
              {vendor.offerings.map((offering) => (
                <OfferingItem key={offering.claim_id} offering={offering} />
              ))}
            </ul>
            <VendorFacts label="Marked" facts={vendor.markets} />
            <VendorFacts label="Sprog" facts={vendor.languages} />
            <p className="vendor-customers">
              {vendor.customers.length > 0 ? (
                <>
                  <strong>Dokumenterede kunder:</strong>{" "}
                  {vendor.customers.join(", ")}
                </>
              ) : (
                <span className="cell-sub">
                  Ingen dokumenterede kunder endnu
                </span>
              )}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}

export default async function VendorsPage({
  searchParams,
}: {
  searchParams: Promise<{ norden?: string }>;
}) {
  const { norden } = await searchParams;
  const nordicOnly = norden === "1";
  let landscape: VendorLandscape | null = null;
  let loadError: unknown = null;
  try {
    landscape = await getVendorLandscape();
  } catch (error) {
    landscape = null;
    loadError = error;
  }

  if (landscape === null) {
    return (
      <>
        <h1>Leverandører</h1>
        <ApiErrorAlert error={loadError} />
      </>
    );
  }

  // Filter: kun leverandører med dokumenteret marked i Danmark/Norden eller
  // dansk sprog. Uden dokumentation vises de ikke — de er ikke afvist.
  const capabilities = nordicOnly
    ? landscape.capabilities.map((c) => ({
        ...c,
        vendors: c.vendors.filter((v) => v.nordic_documented),
      }))
    : landscape.capabilities;
  const withVendors = capabilities.filter((c) => c.vendors.length > 0);
  const withoutVendors = capabilities.filter(
    (c) => c.vendors.length === 0 && c.technology !== null,
  );

  return (
    <>
      <h1>Leverandører</h1>
      <p className="page-lead">
        Hvilke leverandører tilbyder hvilken AI-teknologi til kundecentre — og
        hvilke organisationer bruger dem. Kun godkendte claims med ordret
        evidensuddrag. Udsagn fra leverandørens egne kilder er markeret som
        leverandørens.
      </p>
      <p className="cell-sub">
        {landscape.vendor_count} leverandør(er) · {landscape.offering_count}{" "}
        dokumenterede tilbud ·{" "}
        {nordicOnly ? (
          <>
            Viser kun leverandører med dokumenteret marked i Danmark/Norden
            eller dansk sprog · <Link href="/vendors">Vis alle</Link>
          </>
        ) : (
          <Link href="/vendors?norden=1">
            Vis kun dokumenteret i Danmark/Norden
          </Link>
        )}
      </p>

      {withVendors.length === 0 ? (
        <div className="empty-state">
          <p>
            <strong>Ingen dokumenterede leverandørtilbud endnu.</strong>
          </p>
          <p>
            Tilbud udtrækkes fra nye artikler ved næste kørsel (Admin → Kilder →
            Kør nu).
          </p>
        </div>
      ) : (
        <>
          <nav aria-label="Capabilities" className="landscape-capability-head">
            {withVendors.map((capability) => (
              <a key={anchorId(capability)} href={`#${anchorId(capability)}`}>
                {capability.capability_name} ({capability.vendors.length})
              </a>
            ))}
          </nav>
          {withVendors.map((capability) => (
            <CapabilitySection
              key={anchorId(capability)}
              capability={capability}
            />
          ))}
        </>
      )}

      {withoutVendors.length > 0 ? (
        <p className="cell-sub">
          Ingen dokumenterede leverandører endnu:{" "}
          {withoutVendors.map((c) => c.capability_name).join(", ")}
        </p>
      ) : null}
    </>
  );
}
