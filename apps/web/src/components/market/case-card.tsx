import Link from "next/link";
import type { MarketCase } from "../../app/lib/api";
import { AiNote } from "./ai-note";
import { HideButton } from "./hide-button";

const AREA_LABELS: Record<string, string> = {
  salg: "Salg",
  kundeservice: "Kundeservice",
  support: "Support",
};

export function CaseCard({ item, isAdmin }: { item: MarketCase; isAdmin: boolean }) {
  const technology = item.technology?.label ?? item.technology_name;
  const origin = [item.country, item.industry].filter(Boolean).join(" · ");
  return (
    <article className="market-card" id={`case-${item.id}`}>
      <header className="market-card-head">
        <div>
          <h3 className="market-card-title">{item.company}</h3>
          <p className="market-card-meta">
            {origin ? `${origin} · ` : ""}
            {item.region_label}
          </p>
        </div>
        <span className="area-badges">
          {item.areas.map((area) => (
            <span key={area} className="badge badge-muted">
              {AREA_LABELS[area] ?? area}
            </span>
          ))}
        </span>
      </header>

      {item.what_they_did ? <p className="market-card-lead">{item.what_they_did}</p> : null}

      <dl className="market-facts">
        <div>
          <dt>Teknologi</dt>
          <dd>
            {item.technology ? (
              <Link href={`/teknologier#tech-${item.technology.id}`}>{technology}</Link>
            ) : (
              (technology ?? "Ikke oplyst")
            )}
          </dd>
        </div>
        <div>
          <dt>Leverandør</dt>
          <dd>{item.vendor ?? "Ikke oplyst"}</dd>
        </div>
        <div>
          <dt>Indført</dt>
          <dd>{item.stage_label ?? "Ikke oplyst"}</dd>
        </div>
      </dl>
      {item.scope ? (
        <p className="market-lesson">
          <span className="market-effect-label">Omfang</span> {item.scope}
        </p>
      ) : null}

      <div className={item.effect ? "market-effect" : "market-effect market-effect-none"}>
        <span className="market-effect-label">Effekt</span>
        {item.effect ? (
          <>
            <strong>{item.effect}</strong>
            <span className="cell-sub">
              {[item.kpi_label, item.effect_source_label].filter(Boolean).join(" · ")}
            </span>
          </>
        ) : (
          <span>Ikke oplyst</span>
        )}
      </div>

      {item.lesson ? (
        <p className="market-lesson">
          <span className="market-effect-label">Læring</span> {item.lesson}
        </p>
      ) : null}

      <details className="market-quote">
        <summary>Se citat fra kilden</summary>
        <blockquote className="evidence-quote">{item.quote}</blockquote>
      </details>

      <footer className="market-card-foot">
        <span>
          Kilde:{" "}
          {item.source.url ? (
            <a href={item.source.url} target="_blank" rel="noreferrer">
              {item.source.name}
            </a>
          ) : (
            item.source.name
          )}
          {item.source.vendor_source ? " (leverandør)" : ""}
          {item.also_reported_by.length > 0
            ? ` · også omtalt af ${item.also_reported_by.join(", ")}`
            : ""}
        </span>
        <span className="market-card-tools">
          <AiNote />
          {isAdmin ? <HideButton itemIds={item.item_ids} /> : null}
        </span>
      </footer>
    </article>
  );
}
