import { EmptyState } from "../components/EmptyState";

export default function SourcesPage() {
  return (
    <>
      <h1>Kilder og metode</h1>
      <p className="page-lead">
        Source Registry, kildetyper, seneste kontrol og provenance-principper.
        Hver observation skal kunne åbnes tilbage til dokumentation.
      </p>
      <EmptyState slice="Slice 1">
        Source Registry og de første ingestion-metoder (RSS, web fetch, manuel
        upload) er ikke bygget endnu.
      </EmptyState>
    </>
  );
}
