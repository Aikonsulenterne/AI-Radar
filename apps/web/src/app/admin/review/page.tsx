import Link from "next/link";
import { listDocuments, type DocumentRow } from "../../lib/api";

export const dynamic = "force-dynamic";

const STATUS_LABELS: Record<DocumentRow["processing_status"], string> = {
  discovered: "Opdaget",
  fetched: "Hentet",
  normalized: "Normaliseret",
  classified_relevant: "Relevant",
  classified_irrelevant: "Ikke relevant",
  extraction_pending: "Afventer udtræk",
  review_pending: "Afventer review",
  partially_reviewed: "Delvist reviewet",
  reviewed: "Reviewet",
  failed: "Fejlet",
};

function formatDate(value: string): string {
  return new Intl.DateTimeFormat("da-DK", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Europe/Copenhagen",
  }).format(new Date(value));
}

export default async function ReviewPage() {
  let documents: DocumentRow[] | null = null;
  try {
    documents = (await listDocuments()).items;
  } catch {
    documents = null;
  }

  return (
    <>
      <h1>Review</h1>
      <p className="page-lead">
        Dokumenter i pipelinen. Åbn et dokument for at køre AI-behandling og
        reviewe foreslåede claims med evidensuddrag.
      </p>

      {documents === null ? (
        <div className="alert-error" role="alert">
          API&#8217;et kunne ikke nås, eller din rolle giver ikke adgang til
          review (kræver Reviewer eller Admin).
        </div>
      ) : documents.length === 0 ? (
        <div className="empty-state">
          <p>
            <strong>Ingen dokumenter endnu.</strong>
          </p>
          <p>
            Hent eller upload dokumenter fra Source Registry, så vises de her
            med behandlingsstatus.
          </p>
        </div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">Titel</th>
              <th scope="col">Status</th>
              <th scope="col">MIME</th>
              <th scope="col">Hentet</th>
              <th scope="col">Demo</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => (
              <tr key={doc.id}>
                <td>
                  <Link href={`/admin/review/${doc.id}`}>
                    {doc.title ?? "(uden titel)"}
                  </Link>
                  {doc.canonical_url ? (
                    <span className="cell-sub">{doc.canonical_url}</span>
                  ) : null}
                </td>
                <td>
                  <span className="badge badge-muted">
                    {STATUS_LABELS[doc.processing_status]}
                  </span>
                </td>
                <td>{doc.mime_type ?? "–"}</td>
                <td>{formatDate(doc.retrieved_at)}</td>
                <td>{doc.is_demo ? "Demo" : "Nej"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
