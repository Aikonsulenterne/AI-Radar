import type { MarketCase } from "../../app/lib/api";
import { OutcomeControl } from "./outcome-control";

// Tekst og form, ikke kun farve.
const OUTCOME_MARKS: Record<string, string> = { positiv: "✓", negativ: "✕", blandet: "±" };

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

/** Én case: virksomhed, land, teknologi, fase, hvad de gjorde, resultat og
 * læring. Omfang, start og citat står, når kortet foldes ud. */
export function CaseCard({ item, isAdmin = false }: { item: MarketCase; isAdmin?: boolean }) {
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
        {item.peer_group ? (
          <span className="pill pill-peer">Ligner OK · {item.peer_group}</span>
        ) : null}
        <span className="pill pill-tech">{technology}</span>
        <span className="pill">Leverandør: {item.vendor ?? "Ikke oplyst"}</span>
      </div>
      {at >= 0 ? (
        <ol className="stage-steps" aria-label={`Fase: ${item.stage_label}`}>
          {STAGES.map((s, i) => (
            <li key={s.key} className={i <= at ? "on" : undefined}>
              {s.label}
            </li>
          ))}
        </ol>
      ) : (
        <p className="stage-unknown">Fase ikke oplyst i kilden</p>
      )}
      {item.what_they_did ? <p className="case-what">{item.what_they_did}</p> : null}
      <div className={`box-fact${item.outcome ? ` outcome-${item.outcome}` : ""}`}>
        <div className="result-head">
          <span className="box-label">Resultat</span>
          {item.outcome ? (
            <span className={`outcome-badge outcome-badge-${item.outcome}`}>
              <span aria-hidden="true">{OUTCOME_MARKS[item.outcome]}</span> {item.outcome_label}
            </span>
          ) : null}
        </div>
        {item.effect ? (
          <>
            <p>»{item.effect}«</p>
            <p className="muted small">{item.source_kind_label}</p>
          </>
        ) : (
          <p className="muted">Effekt ikke oplyst</p>
        )}
        {item.lesson ? (
          <p className="case-lesson">
            <strong>Læring:</strong> »{item.lesson}«
          </p>
        ) : null}
      </div>
      {isAdmin ? <OutcomeControl item={item} /> : null}
      <details className="case-more">
        <summary>Omfang, start og citat</summary>
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
