import Link from "next/link";
import { getDocument, type DocumentReview } from "../../../lib/api";
import { DocumentControls } from "./ReviewControls";
import { ReviewWorkbench } from "./ReviewWorkbench";
import { ApiErrorAlert } from "../../../../components/states/api-error";

export const dynamic = "force-dynamic";

export default async function ReviewDocumentPage({
  params,
}: {
  params: Promise<{ documentId: string }>;
}) {
  const { documentId } = await params;
  let doc: DocumentReview | null = null;
  let loadError: unknown = null;
  try {
    doc = await getDocument(documentId);
  } catch (error) {
    doc = null;
    loadError = error;
  }

  if (doc === null) {
    return (
      <>
        <h1>Review</h1>
        <ApiErrorAlert
          error={loadError}
          notFound="Dokumentet findes ikke (det kan være slettet)."
        />
        <p>
          <Link href="/admin/review">Tilbage til dokumentlisten</Link>
        </p>
      </>
    );
  }

  return (
    <>
      <p className="cell-sub">
        <Link href="/admin/review">← Dokumentliste</Link>
      </p>
      <h1>{doc.title ?? "(uden titel)"}</h1>
      <p className="page-lead">
        Status: {doc.processing_status} · MIME: {doc.mime_type ?? "–"}
        {doc.canonical_url ? <> · Kilde-URL: {doc.canonical_url}</> : null}
        {doc.raw_url ? (
          <>
            {" "}
            · <a href={doc.raw_url}>Original fil</a>
          </>
        ) : null}
      </p>

      <DocumentControls document={doc} />

      <ReviewWorkbench document={doc} />
    </>
  );
}
