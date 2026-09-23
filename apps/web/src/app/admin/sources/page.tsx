import { listSources, type Source } from "../../lib/api";
import { CreateSourceForm } from "./CreateSourceForm";
import { SourceActions } from "./SourceActions";
import { ApiErrorAlert } from "../../../components/states/api-error";

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

export default async function AdminSourcesPage() {
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
      <h1>Source Registry</h1>
      <p className="page-lead">
        Kuraterede kilder med type, hentemetode, access class og seneste
        kontrol. Hver observation skal kunne spores tilbage hertil.
      </p>

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
                <td>{formatDate(source.last_checked_at)}</td>
                <td>
                  <SourceActions source={source} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
