import { getOkBrief, type OkBrief } from "./lib/api";
import { getRole } from "./lib/me";
import { ApiErrorAlert } from "../components/states/api-error";
import { PrintButton } from "../components/market/print-button";
import { ProblemRow } from "../components/market/problem-row";
import { ApproveBriefButton } from "../components/market/approve-brief-button";
import { SpreadsheetButton } from "../components/market/spreadsheet-button";
import { CompetitorMatrix } from "../components/market/competitor-matrix";
import { DecisionCard } from "../components/market/decision-card";
import { GainLine } from "../components/market/gain-line";

export const dynamic = "force-dynamic";

export default async function TilOkPage() {
  const [result, role] = await Promise.all([
    getOkBrief().then(
      (value) => ({ value }),
      (error: unknown) => ({ error }),
    ),
    getRole(),
  ]);
  const isAdmin = role === "admin";
  if (!("value" in result)) {
    return (
      <>
        <h1>Til OK</h1>
        <ApiErrorAlert error={result.error} />
      </>
    );
  }
  const brief: OkBrief = result.value;
  const empty = brief.case_count === 0 && brief.technology_count === 0;
  const approvedLabel = brief.approved_at
    ? new Intl.DateTimeFormat("da-DK", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
        timeZone: "Europe/Copenhagen",
      }).format(new Date(brief.approved_at))
    : null;

  if (!isAdmin && brief.state === "ingen") {
    return (
      <div className="til-ok">
        <header className="page-head">
          <div>
            <p className="eyebrow">Til OK</p>
            <h1>AI i kundecentret – det korte overblik</h1>
          </div>
        </header>
        <p className="empty-line">
          Til OK er ikke klar endnu. Den opdateres og godkendes hver mandag.
        </p>
      </div>
    );
  }

  return (
    <div className="til-ok">
      <header className="page-head tilok-head">
        <p className="eyebrow">
          Til OK · AI i kundecentret{brief.month_label ? ` · ${brief.month_label}` : ""}
        </p>
        <div className="page-head-actions no-print">
          {!empty ? <SpreadsheetButton /> : null}
          <PrintButton />
        </div>
      </header>

      {isAdmin && brief.state === "kladde" && !empty ? (
        <div className="draft-banner no-print" role="status">
          <div>
            <strong>Kladde.</strong> Direktøren ser{" "}
            {approvedLabel
              ? `den version, du godkendte ${approvedLabel}.`
              : "endnu ingen version."}{" "}
            Tjek siden, og godkend den, når den er rigtig.
          </div>
          <ApproveBriefButton />
        </div>
      ) : null}
      {isAdmin && brief.state === "godkendt" && approvedLabel ? (
        <p className="muted small no-print">
          Godkendt {approvedLabel} · direktøren ser denne version · mail:{" "}
          {brief.mail_status ?? "ikke sendt"}.
        </p>
      ) : null}

      {empty ? (
        <>
        <h1>AI i kundecentret – det korte overblik</h1>
        <p className="empty-line">
          Radaren har ikke fundet noget endnu.{" "}
          {isAdmin
            ? "Gå til Kilder og tryk “Opdatér radaren”."
            : "Kom tilbage senere – radaren opdateres hver uge."}
        </p>
        </>
      ) : (
        <>
          <section className="tilok-headline" aria-label="Det vigtigste lige nu">
            <h1>{brief.headline?.text ?? "Radaren har ikke fundet cases endnu."}</h1>
            {brief.headline?.href && !brief.headline.href.startsWith("#") ? (
              <a href={brief.headline.href}>Se casene →</a>
            ) : null}
          </section>

          <div className="tilok-top">
            <CompetitorMatrix matrix={brief.matrix} />

            <div className="tilok-side">
              <section className="since-last" aria-labelledby="since-title">
                <h2 id="since-title">Siden sidst</h2>
                {brief.since_last.lines.length > 0 ? (
                  <ul>
                    {brief.since_last.lines.map((line) => (
                      <li key={line.text}>
                        {line.href ? <a href={line.href}>{line.text}</a> : line.text}
                        {line.source_url ? (
                          <>
                            {" "}
                            <a
                              className="since-source"
                              href={line.source_url}
                              target="_blank"
                              rel="noreferrer"
                            >
                              Kilde
                            </a>
                          </>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="muted">{brief.since_last.note ?? "Intet nyt."}</p>
                )}
              </section>

              <section className="decisions-v3" id="beslutninger" aria-labelledby="decisions-title">
                <h2 id="decisions-title">Det skal du tage stilling til</h2>
                {brief.follow_ups.length > 0 ? (
                  <ul className="follow-ups">
                    {brief.follow_ups.map((f) => (
                      <li key={f.question}>
                        <strong>{f.label}:</strong> {f.question} <em>Hvor står det?</em>
                      </li>
                    ))}
                  </ul>
                ) : null}
                {brief.decisions.length > 0 ? (
                  <ol className="decision-list">
                    {brief.decisions.map((d) => (
                      <DecisionCard key={d.key} decision={d} />
                    ))}
                  </ol>
                ) : (
                  <p className="muted">Ingen nye beslutninger denne gang.</p>
                )}
              </section>
            </div>
          </div>

          {brief.recommendations.length > 0 ? (
            <section className="recs-v3" aria-labelledby="recs-title">
              <h2 id="recs-title">Det foreslår vi</h2>
              <ol>
                {brief.recommendations.map((r) => (
                  <li key={r.action}>
                    <p className="rec-action">{r.action}</p>
                    <p className="muted small">
                      {[r.owner, r.duration].filter(Boolean).join(" · ")}
                    </p>
                    {r.first_step ? (
                      <p className="rec-line">
                        <span className="rec-key">Denne uge</span> {r.first_step}
                      </p>
                    ) : null}
                    {r.reference || r.vendor ? (
                      <p className="rec-line">
                        <span className="rec-key">Ring til</span>{" "}
                        {r.reference ? (
                          <a href={r.reference.href}>
                            {r.reference.company}
                            {r.reference.country ? ` (${r.reference.country})` : ""}
                          </a>
                        ) : null}
                        {r.reference && r.vendor ? " · " : ""}
                        {r.vendor ? `Leverandør: ${r.vendor}` : ""}
                      </p>
                    ) : null}
                    {r.technology ? (
                      <p className="rec-line">
                        <GainLine gain={r.gain} />
                      </p>
                    ) : null}
                  </li>
                ))}
              </ol>
            </section>
          ) : null}

          {brief.areas.map((area) => (
            <section
              key={area.area}
              className="brief-area-v2"
              aria-labelledby={`area-${area.area}`}
            >
              <h2 id={`area-${area.area}`}>{area.label}</h2>
              <div className="brief-table">
                <div className="brief-grid brief-head-row" aria-hidden="true">
                  <span>Problem</span>
                  <span>Bedste teknologi</span>
                  <span>Stærkeste bevis</span>
                  <span>Næste skridt</span>
                  <span />
                </div>
                {area.rows.map((row) => (
                  <ProblemRow key={row.key} row={row} />
                ))}
              </div>
            </section>
          ))}

          {brief.undocumented.length > 0 ? (
            <section
              className="undocumented"
              aria-label="Endnu ikke dokumenteret"
            >
              <span className="box-label">Endnu ikke dokumenteret</span>
              {brief.undocumented.map((u) => (
                <span key={u.title}>
                  {u.title} <span className="muted">({u.area_label})</span>
                </span>
              ))}
            </section>
          ) : null}
        </>
      )}
    </div>
  );
}
