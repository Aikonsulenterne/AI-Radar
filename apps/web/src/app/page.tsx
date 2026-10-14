import { getOkBrief, type OkBrief } from "./lib/api";
import { getRole } from "./lib/me";
import { ApiErrorAlert } from "../components/states/api-error";
import { PrintButton } from "../components/market/print-button";
import { ProblemRow } from "../components/market/problem-row";
import { ApproveBriefButton } from "../components/market/approve-brief-button";
import { SpreadsheetButton } from "../components/market/spreadsheet-button";

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
      <header className="page-head">
        <div>
          <p className="eyebrow">
            Til OK{brief.month_label ? ` · ${brief.month_label}` : ""}
          </p>
          <h1>AI i kundecentret – det korte overblik</h1>
        </div>
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
        <p className="empty-line">
          Radaren har ikke fundet noget endnu.{" "}
          {isAdmin
            ? "Gå til Kilder og tryk “Opdatér radaren”."
            : "Kom tilbage senere – radaren opdateres hver uge."}
        </p>
      ) : (
        <>
          <div className="brief-top-grid">
            {brief.must_know.length > 0 ? (
              <section className="must-know" aria-labelledby="must-know-title">
                <h2 id="must-know-title">Det skal du vide</h2>
                <ol>
                  {brief.must_know.map((point) => (
                    <li key={point.n}>
                      <span className="must-know-n">{point.n}</span>
                      <span>
                        {point.text}{" "}
                        {point.source_url ? (
                          <a
                            href={point.source_url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Kilde →
                          </a>
                        ) : point.href ? (
                          <a href={point.href}>Kilde →</a>
                        ) : null}
                      </span>
                    </li>
                  ))}
                </ol>
                <p className="ai-note-dark">AI-sammenfattet · tjek kilden</p>
              </section>
            ) : null}

            <div className="brief-pair">
              {brief.recommendations.length > 0 ? (
                <section
                  className="box-recommendation"
                  aria-labelledby="recs-title"
                >
                  <h2 id="recs-title">Det foreslår vi</h2>
                  <ol className="recs">
                    {brief.recommendations.map((r) => (
                      <li key={r.action}>
                        {r.action}
                        <div className="muted small">
                          {[r.owner, r.duration].filter(Boolean).join(" · ")}
                        </div>
                      </li>
                    ))}
                  </ol>
                </section>
              ) : null}

              {brief.decisions.length > 0 ? (
                <section
                  className="box-decision"
                  aria-labelledby="decisions-title"
                >
                  <h2 id="decisions-title">Det skal du tage stilling til</h2>
                  <ul className="decisions">
                    {brief.decisions.map((q) => (
                      <li key={q}>
                        <span className="yes-no">Ja / nej</span>
                        <span>{q}</span>
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}
            </div>
          </div>

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
