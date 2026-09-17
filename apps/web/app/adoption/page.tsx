import { EmptyState } from "../components/EmptyState";

export default function AdoptionPage() {
  return (
    <>
      <h1>AI-adoption</h1>
      <p className="page-lead">
        Virksomheder og dokumenterede cases: capability, use case,
        implementeringsstadie, effekt og evidens. Manglende fakta vises som
        &#8220;Ikke dokumenteret&#8221; og gættes aldrig.
      </p>
      <EmptyState slice="Slice 4">
        Adoption cases kræver godkendte claims med evidensuddrag.
      </EmptyState>
    </>
  );
}
