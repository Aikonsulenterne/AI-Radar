import type { MarketCase } from "../../app/lib/api";

const STAGES = [
  { key: "idé", label: "Idé" },
  { key: "pilot", label: "Pilot" },
  { key: "drift", label: "Drift" },
  { key: "skaleret", label: "Skaleret" },
];

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("da-DK", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "Europe/Copenhagen",
  }).format(new Date(value));
}

/** Én case: virksomhed, land, teknologi, trin, hvad de gjorde og effekt.
 * Læring, omfang, start og kilde står, når kortet foldes ud. */
export function CaseCard({ item }: { item: MarketCase }) {
  const at = STAGES.findIndex((s) => s.key === item.stage);
  const technology = item.technology?.label ?? item.technology_name ?? "Ikke oplyst";
  const origin = [item.country_label, item.industry].filter(Boolean).join(" · ");
  return (
    <article className="case-v2" id={`case-${item.id}`}>
      <header className="case-v2-head">
        <h2>{item.company}</h2>
        {origin ? <span className="muted small">{origin}</span> : null}
      </header>
      <div className="pill-list">
        <span className="pill pill-tech">{technology}</span>
        <span className="pill">Leverandør: {item.vendor ?? "Ikke oplyst"}</span>
      </div>
      <ol className="stage-steps" aria-label={`Status: ${item.stage_label ?? "Ikke oplyst"}`}>
        {STAGES.map((s, i) => (
          <li key={s.key} className={at >= 0 && i <= at ? "on" : undefined}>
            {s.label}
          </li>
        ))}
      </ol>
      {item.what_they_did ? <p className="case-what">{item.what_they_did}</p> : null}
      <div className="box-fact">
        <span className="box-label">Effekt</span>
        {item.effect ? (
          <>
            <p>»{item.effect}«</p>
            <p className="muted small">{item.source_kind_label}</p>
          </>
        ) : (
          <p className="muted">Ikke oplyst</p>
        )}
      </div>
      <details className="case-more">
        <summary>Læring, omfang og kilde</summary>
        {item.lesson ? (
          <div className="box-analysis">
            <span className="box-label">Læring ifølge kilden</span>
            <p>»{item.lesson}«</p>
          </div>
        ) : null}
        <dl className="case-facts">
          <dt>Start</dt>
          <dd>{item.start ?? "Ikke oplyst"}</dd>
          <dt>Omfang</dt>
          <dd>{item.scope ?? "Ikke oplyst"}</dd>
        </dl>
        <blockquote className="evidence-quote">{item.quote}</blockquote>
      </details>
      <footer className="tech-foot">
        {item.source.url ? (
          <a href={item.source.url} target="_blank" rel="noreferrer">
            Kilde: {item.source.title ?? item.source.name} · {formatDate(item.observed_at)} →
          </a>
        ) : (
          <span>
            Kilde: {item.source.name} · {formatDate(item.observed_at)}
          </span>
        )}
      </footer>
    </article>
  );
}
