import { EmptyState } from "./components/EmptyState";

export default function OverblikPage() {
  return (
    <>
      <h1>Overblik</h1>
      <p className="page-lead">
        Vigtigste publicerede signaler, KPI&#8217;er med kilde, teknologier i
        NU/NÆSTE/HORIZON, adoption cases og opportunity-kandidater.
      </p>
      <EmptyState slice="Slice 3">
        Overblikket viser kun verificerede signaler. Der er endnu ingen
        publicerede signaler, fordi ingestion- og review-kæden ikke er bygget.
      </EmptyState>
    </>
  );
}
