import { EmptyState } from "../../components/EmptyState";

export default function AdminSourcesPage() {
  return (
    <>
      <h1>Source Registry</h1>
      <p className="page-lead">
        Administration af kilder: type, hentemetode (RSS, web fetch, manuel
        upload), frekvens, access class og status.
      </p>
      <EmptyState slice="Slice 1">
        Source-administration bygges sammen med den første ingestion-metode.
        Adgang bliver rollestyret (Admin) server-side.
      </EmptyState>
    </>
  );
}
