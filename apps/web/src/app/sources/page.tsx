import { listSources, type Source } from "../lib/api";
import { ApiErrorAlert } from "../../components/states/api-error";

export const dynamic = "force-dynamic";

const RETRIEVAL_LABELS: Record<Source["retrieval_method"], string> = {
  rss: "RSS",
  web_fetch: "Web fetch",
  manual_upload: "Manuel upload",
};

function formatDate(value: string | null): string {
  if (!value) return "–";
  return new Intl.DateTimeFormat("da-DK", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Europe/Copenhagen",
  }).format(new Date(value));
}

export default async function SourcesPage() {
  let sources: Source[] | null = null;
  let loadError: unknown = null;
  try {
    sources = (await listSources()).items;
  } catch (error) {
    sources = null;
    loadError = error;
  }

  return (
    <>
      <h1>Kilder og metode</h1>
      <p className="page-lead">
        Alle publicerede fakta kan spores: kilde → dokument → atomic claim →
        evidensuddrag → menneskeligt review. Kildetype er ikke det samme som
        sandhedsstatus, og systemet omgår aldrig paywalls eller
        adgangskontrol.
      </p>

      {sources === null ? (
        <ApiErrorAlert error={loadError} />
      ) : sources.length === 0 ? (
        <div className="empty-state">
          <p>
            <strong>Ingen registrerede kilder endnu.</strong>
          </p>
          <p>Kilder administreres i Source Registry under Administration.</p>
        </div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">Kilde</th>
              <th scope="col">Kildetype</th>
              <th scope="col">Hentemetode</th>
              <th scope="col">Access class</th>
              <th scope="col">Senest kontrolleret</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {sources.map((source) => (
              <tr key={source.id}>
                <td>
                  {source.name}
                  {source.base_url ? (
                    <span className="cell-sub">{source.base_url}</span>
                  ) : null}
                </td>
                <td>{source.source_type}</td>
                <td>{RETRIEVAL_LABELS[source.retrieval_method]}</td>
                <td>{source.access_class}</td>
                <td>{formatDate(source.last_checked_at)}</td>
                <td>
                  <span
                    className={
                      source.active ? "badge badge-ok" : "badge badge-muted"
                    }
                  >
                    {source.active ? "Aktiv" : "Deaktiveret"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
