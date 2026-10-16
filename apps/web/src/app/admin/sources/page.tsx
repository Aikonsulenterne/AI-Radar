import {
  getMarketCases,
  getMarketSources,
  getMarketTechnologies,
  getOkPublicStatus,
  listSources,
  type MarketCase,
  type MarketSource,
  type MarketTechnology,
  type OkPublicStatusRow,
  type Source,
} from "../../lib/api";
import { CreateSourceForm } from "./CreateSourceForm";
import { SourceActions } from "./SourceActions";
import { ApiErrorAlert } from "../../../components/states/api-error";
import { HideButton } from "../../../components/market/hide-button";
import { UpdateRadarButton } from "../../../components/market/update-radar-button";
import { GenerateBriefButton } from "../../../components/market/generate-brief-button";
import { OkStatusForm } from "../../../components/market/ok-status-form";

export const dynamic = "force-dynamic";

const RETRIEVAL_LABELS: Record<Source["retrieval_method"], string> = {
  rss: "RSS",
  web_fetch: "Web fetch",
  manual_upload: "Manuel upload",
};

const FREQUENCY_LABELS: Record<Source["frequency"], string> = {
  manual: "Manuel",
  daily: "Dagligt",
  weekly: "Ugentligt",
  monthly: "Månedligt",
};

function formatDate(value: string | null): string {
  if (!value) return "–";
  return new Intl.DateTimeFormat("da-DK", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Europe/Copenhagen",
  }).format(new Date(value));
}

export default async function AdminSourcesPage() {
  let sources: Source[] | null = null;
  let marketSources: MarketSource[] | null = null;
  let cases: MarketCase[] = [];
  let technologies: MarketTechnology[] = [];
  let okStatus: OkPublicStatusRow[] = [];
  let loadError: unknown = null;
  try {
    const [all, market, caseData, techData, status] = await Promise.all([
      listSources(),
      getMarketSources(),
      getMarketCases({}),
      getMarketTechnologies(),
      getOkPublicStatus(),
    ]);
    okStatus = status;
    sources = all.items;
    marketSources = market;
    cases = caseData.items;
    technologies = techData.items;
  } catch (error) {
    sources = null;
    loadError = error;
  }
  const offers = technologies.flatMap((t) =>
    t.vendors
      .filter((v) => !v.via_case && v.item_ids.length > 0)
      .map((v) => ({
        key: `${t.id}-${v.name}`,
        vendor: v.name,
        tech: t.label,
        ids: v.item_ids,
      })),
  );

  return (
    <div className="market-v2">
      <header className="page-head">
        <div className="page-intro">
          <p className="eyebrow">Kilder · kun admin</p>
          <h1>Hvor henter radaren sin viden?</h1>
          <p>
            Radaren læser disse kilder og opdaterer siderne automatisk hver
            mandag. Interne OK-dokumenter indgår ikke som markedsviden.
          </p>
        </div>
        <div className="page-head-actions">
          <GenerateBriefButton />
          <UpdateRadarButton />
        </div>
      </header>

      {marketSources === null ? (
        <ApiErrorAlert error={loadError} />
      ) : (
        <div className="table-card">
          <table className="v2-table">
            <thead>
              <tr>
                <th scope="col">Kilde</th>
                <th scope="col">Type</th>
                <th scope="col">Senest læst</th>
                <th scope="col" className="num">
                  Relevante artikler
                </th>
              </tr>
            </thead>
            <tbody>
              {marketSources.map((s) => (
                <tr key={s.id}>
                  <th scope="row">
                    {s.name}
                    {s.active ? null : (
                      <span className="muted small"> (sat på pause)</span>
                    )}
                  </th>
                  <td className="muted">{s.type}</td>
                  <td className="muted">{formatDate(s.last_checked_at)}</td>
                  <td className="num">{s.relevant_articles}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {cases.length > 0 || offers.length > 0 ? (
        <section
          className="v2-section"
          aria-labelledby="hide-title"
          style={{ marginTop: 34 }}
        >
          <div className="v2-section-head">
            <h2 id="hide-title">Skjul forkerte fund</h2>
            <span className="muted">
              Et skjult fund forsvinder fra alle sider. Intet slettes, og
              handlingen står i audit-loggen.
            </span>
          </div>
          <div className="brief-pair">
            <div className="table-card">
              <ul className="hide-list" aria-label="Cases">
                {cases.map((c) => (
                  <li key={c.id}>
                    <span>
                      <strong>{c.company}</strong>{" "}
                      <span className="muted">
                        ·{" "}
                        {c.technology?.label ??
                          c.technology_name ??
                          "Ikke oplyst"}
                      </span>
                    </span>
                    <HideButton itemIds={c.item_ids} />
                  </li>
                ))}
              </ul>
            </div>
            <div className="table-card">
              <ul className="hide-list" aria-label="Leverandører">
                {offers.map((o) => (
                  <li key={o.key}>
                    <span>
                      <strong>{o.vendor}</strong>{" "}
                      <span className="muted">· {o.tech}</span>
                    </span>
                    <HideButton itemIds={o.ids} />
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      ) : null}

      <details className="admin-tools">
        <summary>OK&rsquo;s offentlige brug af AI (OK-rækken i konkurrentoverblikket)</summary>
        <p className="muted small">
          Kun det, alle kan se, fx en chatbot på ok.dk. Angiv siden som kilde. Aldrig interne
          oplysninger.
        </p>
        <OkStatusForm rows={okStatus} />
      </details>

      <details className="admin-tools">
        <summary>Administrér kilder</summary>
        <CreateSourceForm />

        {sources === null ? (
          <ApiErrorAlert error={loadError} />
        ) : sources.length === 0 ? (
          <div className="empty-state">
            <p>
              <strong>Ingen kilder endnu.</strong>
            </p>
            <p>Opret den første kilde ovenfor.</p>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th scope="col">Navn</th>
                <th scope="col">Type</th>
                <th scope="col">Hentemetode</th>
                <th scope="col">Access</th>
                <th scope="col">Status</th>
                <th scope="col">Frekvens</th>
                <th scope="col">Senest kontrolleret</th>
                <th scope="col">Handlinger</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((source) => (
                <tr key={source.id}>
                  <td>
                    {source.name}
                    {source.endpoint_url ? (
                      <span className="cell-sub">{source.endpoint_url}</span>
                    ) : null}
                  </td>
                  <td>{source.source_type}</td>
                  <td>{RETRIEVAL_LABELS[source.retrieval_method]}</td>
                  <td>{source.access_class}</td>
                  <td>
                    <span
                      className={
                        source.active ? "badge badge-ok" : "badge badge-muted"
                      }
                    >
                      {source.active ? "Aktiv" : "Deaktiveret"}
                    </span>
                  </td>
                  <td>
                    {FREQUENCY_LABELS[source.frequency]}
                    {source.frequency !== "manual" && source.next_check_at ? (
                      <span className="cell-sub">
                        Næste: {formatDate(source.next_check_at)}
                      </span>
                    ) : null}
                  </td>
                  <td>{formatDate(source.last_checked_at)}</td>
                  <td>
                    <SourceActions source={source} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </details>
    </div>
  );
}
