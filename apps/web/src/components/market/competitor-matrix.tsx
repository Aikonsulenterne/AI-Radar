import type { MatrixState, OkMatrix } from "../../app/lib/api";

function shortDate(value: string): string {
  return new Intl.DateTimeFormat("da-DK", {
    day: "numeric",
    month: "short",
    timeZone: "Europe/Copenhagen",
  }).format(new Date(value));
}

// Form og tekst, ikke kun farve: fyldt prik = drift, halv = pilot, ring =
// omtalt, streg = ikke fundet i kilderne (ikke: "bruger det ikke").
function Mark({ state }: { state: MatrixState }) {
  return <span className={`cm-mark cm-mark-${state}`} aria-hidden="true" />;
}

function Cell({
  cell,
}: {
  cell: OkMatrix["rows"][number]["cells"][number];
}) {
  const content = (
    <>
      <Mark state={cell.state} />
      <span>{cell.label}</span>
    </>
  );
  if (!cell.href) return <span className={`cm-cell cm-${cell.state}`}>{content}</span>;
  const external = cell.href.startsWith("http");
  return (
    <a
      className={`cm-cell cm-${cell.state}`}
      href={cell.href}
      {...(external ? { target: "_blank", rel: "noreferrer" } : {})}
    >
      {content}
    </a>
  );
}

/** Dem, der ligner OK × teknologier. Beregnet af serveren; hver celle med
 * en case linker til casen og dens kilde. */
export function CompetitorMatrix({ matrix }: { matrix: OkMatrix }) {
  const peers = matrix.rows.filter((r) => !r.is_ok).length;
  return (
    <section className="cm" id="overblik" aria-labelledby="cm-title">
      <div className="cm-head">
        <h2 id="cm-title">Dem, der ligner OK</h2>
        <span className="muted small">
          {peers} af {matrix.peer_total} har en dokumenteret AI-case
          {matrix.searched_at ? ` · søgt i kilderne ${shortDate(matrix.searched_at)}` : ""}
        </span>
      </div>
      {matrix.rows.length === 0 ? (
        <p className="empty-line">
          Ingen af de {matrix.peer_total} selskaber, der ligner OK, har en dokumenteret AI-case
          endnu.
        </p>
      ) : (
        <>
          <table className="cm-table">
            <thead>
              <tr>
                <th scope="col">
                  <span className="sr-only">Selskab</span>
                </th>
                {matrix.columns.map((c) => (
                  <th key={c.id} scope="col">
                    {c.label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matrix.rows.map((row) => (
                <tr key={row.name} className={row.is_ok ? "cm-ok" : undefined}>
                  <th scope="row">
                    {row.name}
                    {row.group ? <span className="cm-group">{row.group}</span> : null}
                  </th>
                  {row.cells.map((cell, i) => (
                    <td key={matrix.columns[i]?.id ?? i}>
                      <Cell cell={cell} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <ul className="cm-list">
            {matrix.rows.map((row) => (
              <li key={row.name} className={row.is_ok ? "cm-ok" : undefined}>
                <strong>{row.name}</strong>
                <span className="cm-chips">
                  {row.cells.map((cell, i) =>
                    cell.state === "ingen" ? null : (
                      <span key={matrix.columns[i]?.id ?? i} className="cm-chip">
                        <span className="cm-chip-label">{matrix.columns[i]?.label}:</span>{" "}
                        <Cell cell={cell} />
                      </span>
                    ),
                  )}
                  {row.cells.every((c) => c.state === "ingen") ? (
                    <span className="muted">Ikke fundet i kilderne</span>
                  ) : null}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
      <p className="cm-legend muted small">
        <span>
          <Mark state="drift" /> Drift
        </span>
        <span>
          <Mark state="pilot" /> Pilot
        </span>
        <span>
          <Mark state="omtalt" /> Omtalt, fase ikke oplyst
        </span>
        <span>
          <Mark state="ingen" /> Ikke fundet i kilderne (betyder ikke, at de ikke bruger det)
        </span>
        {matrix.more_columns > 0 ? (
          <span>{matrix.more_columns} teknologier mere under Sådan gør andre</span>
        ) : null}
      </p>
      {matrix.peers_without.length > 0 ? (
        <p className="muted small">
          Ikke fundet i kilderne endnu: {matrix.peers_without.join(" · ")}
        </p>
      ) : null}
    </section>
  );
}
