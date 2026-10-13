import Link from "next/link";
import {
  getOkBrief,
  type MarketArea,
  type OkBrief,
  type OkBriefProblem,
} from "./lib/api";
import { formatDateTime } from "./lib/labels";
import { getRole } from "./lib/me";
import { ApiErrorAlert } from "../components/states/api-error";
import { AREA_TABS, FilterTabs } from "../components/market/area-tabs";
import { AiNote } from "../components/market/ai-note";
import { PrintButton } from "./beslutningsoplaeg/PrintButton";
import { GenerateBriefButton } from "../components/market/generate-brief-button";

export const dynamic = "force-dynamic";

const AREAS: MarketArea[] = ["salg", "kundeservice", "support"];

function hasFindings(problem: OkBriefProblem): boolean {
  return problem.technologies.length > 0 || problem.cases.length > 0;
}

function ProblemCard({ problem }: { problem: OkBriefProblem }) {
  const effect = problem.effects[0];
  const vendors = problem.contacts.filter((c) => c.kind === "leverandør");
  const references = problem.contacts.filter((c) => c.kind === "reference");
  return (
    <article className="problem-brief" id={`problem-${problem.key}`}>
      <h3 className="problem-brief-title">{problem.name}</h3>

      {problem.technologies.length > 0 ? (
        <ul className="fact-chips" aria-label="Teknologier, der løser det">
          {problem.technologies.map((t) => (
            <li className="fact-chip" key={t.id}>
              <Link href={`/teknologier#tech-${t.id}`}>{t.label}</Link>
            </li>
          ))}
        </ul>
      ) : null}

      {effect ? (
        <p className="problem-brief-effect">
          <span className="market-effect-label">Effekt hos andre</span>
          <strong>
            {effect.company}: {effect.effect}
          </strong>
          {effect.effect_source_label ? (
            <span className="cell-sub">{effect.effect_source_label}</span>
          ) : null}
        </p>
      ) : null}

      {problem.next_step ? (
        <p className="problem-brief-next">
          <span className="market-effect-label">Næste skridt</span>
          {problem.next_step}
        </p>
      ) : null}

      {problem.cases.length > 0 || problem.contacts.length > 0 ? (
        <details className="problem-brief-more">
          <summary>
            Se cases og hvem vi kan tale med
          </summary>
          {problem.cases.length > 0 ? (
            <>
              <h4>Sammenlignelige cases</h4>
              <ul>
                {problem.cases.map(({ case: c, why }) => (
                  <li key={c.id}>
                    <Link href={`/cases#case-${c.id}`}>{c.company}</Link>
                    {c.region_label ? ` (${c.region_label})` : ""}
                    {why ? ` — ${why}` : ""}
                  </li>
                ))}
              </ul>
            </>
          ) : null}
          {problem.effects.length > 1 ? (
            <>
              <h4>Dokumenteret effekt</h4>
              <ul>
                {problem.effects.map((e) => (
                  <li key={`${e.company}-${e.effect}`}>
                    {e.company}: {e.effect}
                    {e.kpi_label ? ` (${e.kpi_label})` : ""}{" "}
                    {e.source_url ? (
                      <a href={e.source_url} target="_blank" rel="noreferrer">
                        kilde
                      </a>
                    ) : null}
                  </li>
                ))}
              </ul>
            </>
          ) : null}
          {vendors.length > 0 ? (
            <>
              <h4>Leverandører</h4>
              <p>
                {vendors
                  .map((v) => (v.danish_supported ? `${v.name} (dansk)` : v.name))
                  .join(", ")}
              </p>
            </>
          ) : null}
          {references.length > 0 ? (
            <>
              <h4>Referencer</h4>
              <p>{references.map((r) => r.name).join(", ")}</p>
            </>
          ) : null}
        </details>
      ) : null}
    </article>
  );
}

function AreaSection({
  area,
  problems,
}: {
  area: MarketArea;
  problems: OkBriefProblem[];
}) {
  const withFindings = problems.filter(hasFindings);
  const without = problems.filter((p) => !hasFindings(p));
  const label = problems[0]?.area_label;
  if (!label) return null;
  return (
    <section className="brief-area" aria-label={label} data-area={area}>
      <h2 className="section-title">{label}</h2>
      {withFindings.length > 0 ? (
        <div className="problem-grid">
          {withFindings.map((p) => (
            <ProblemCard key={p.key} problem={p} />
          ))}
        </div>
      ) : null}
      {without.length > 0 ? (
        <p className="cell-sub brief-gaps">
          Endnu ingen dokumentation for: {without.map((p) => p.name).join(" · ")}
        </p>
      ) : null}
    </section>
  );
}

export default async function TilOkPage({
  searchParams,
}: {
  searchParams: Promise<{ omraade?: string }>;
}) {
  const { omraade } = await searchParams;
  const area = AREAS.includes(omraade as MarketArea) ? (omraade as MarketArea) : undefined;

  let brief: OkBrief | null = null;
  let loadError: unknown = null;
  const [briefResult, role] = await Promise.all([
    getOkBrief(area).then(
      (value) => ({ value }),
      (error: unknown) => ({ error }),
    ),
    getRole(),
  ]);
  if ("value" in briefResult) brief = briefResult.value;
  else loadError = briefResult.error;
  const isAdmin = role === "admin";

  if (brief === null) {
    return (
      <>
        <h1>Til OK</h1>
        <ApiErrorAlert error={loadError} />
      </>
    );
  }

  const empty = brief.case_count === 0 && brief.technology_count === 0;
  const areas = area ? [area] : AREAS;

  return (
    <div className="brief-page">
      <header className="brief-head">
        <div>
          <h1>Til OK</h1>
          <p className="page-lead">
            Hvad AI kan gøre for Salg, Kundeservice og Support — bygget på{" "}
            {brief.case_count} cases og {brief.technology_count} teknologier fra
            radarens kilder.
          </p>
          <p className="cell-sub">
            {brief.generated_at
              ? `Opdateret ${formatDateTime(brief.generated_at)} · `
              : ""}
            <AiNote />
          </p>
        </div>
        <div className="brief-actions no-print">
          <PrintButton />
          {isAdmin ? <GenerateBriefButton /> : null}
        </div>
      </header>

      <FilterTabs
        label="Område"
        param="omraade"
        tabs={AREA_TABS}
        current={area}
        basePath="/"
        params={{}}
      />

      {empty ? (
        <div className="empty-state">
          <p>
            <strong>Radaren har ikke fundet noget endnu.</strong>
          </p>
          <p>
            {isAdmin
              ? "Gå til Kilder og tryk “Opdatér radaren”. Første kørsel tager nogle minutter."
              : "Kom tilbage senere — radaren opdateres hver uge."}
          </p>
        </div>
      ) : (
        <>
          {brief.top_now.length > 0 ? (
            <section className="brief-top" aria-label="Det vigtigste lige nu">
              <h2 className="section-title">Det vigtigste lige nu</h2>
              <ol>
                {brief.top_now.map((point) => (
                  <li key={point.text}>
                    {point.text}{" "}
                    <span className="cell-sub brief-refs">
                      {point.cases.map((c) =>
                        c.source_url ? (
                          <a key={c.id} href={c.source_url} target="_blank" rel="noreferrer">
                            {c.company}
                          </a>
                        ) : (
                          <Link key={c.id} href={`/cases#case-${c.id}`}>
                            {c.company}
                          </Link>
                        ),
                      )}
                      {point.technologies.map((t) => (
                        <Link key={t.id} href={`/teknologier#tech-${t.id}`}>
                          {t.label}
                        </Link>
                      ))}
                    </span>
                  </li>
                ))}
              </ol>
            </section>
          ) : null}

          {areas.map((a) => (
            <AreaSection
              key={a}
              area={a}
              problems={brief.problems.filter((p) => p.area === a)}
            />
          ))}
        </>
      )}
    </div>
  );
}
