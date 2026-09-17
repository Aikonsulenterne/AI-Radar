import { EmptyState } from "../../components/EmptyState";

export default function ReviewPage() {
  return (
    <>
      <h1>Review</h1>
      <p className="page-lead">
        Review Queue pr. dokument: original kilde, foreslåede claims,
        evidensuddrag, entities samt mulige dubletter og konflikter. Handlinger:
        Approve, Edit and approve, Needs corroboration, Reject.
      </p>
      <EmptyState slice="Slice 2">
        Review kræver claim extraction og evidensuddrag fra
        ingestion-pipelinen. Adgang bliver rollestyret (Reviewer/Admin)
        server-side.
      </EmptyState>
    </>
  );
}
