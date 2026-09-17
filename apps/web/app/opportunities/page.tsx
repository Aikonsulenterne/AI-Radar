import { EmptyState } from "../components/EmptyState";

export default function OpportunitiesPage() {
  return (
    <>
      <h1>Opportunities</h1>
      <p className="page-lead">
        Ekstern udvikling &#215; dokumentation &#215; relevant OK-problem =
        opportunity-kandidat. Pipeline: Identificeret → Undersøges → Business
        case → Pilot → Skalering → Afsluttet. AI må foreslå; et menneske
        godkender.
      </p>
      <EmptyState slice="Slice 5">
        Opportunities kobles til signaler, claims og problem-taxonomien.
      </EmptyState>
    </>
  );
}
