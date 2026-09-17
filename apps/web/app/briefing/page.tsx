import { EmptyState } from "../components/EmptyState";

export default function BriefingPage() {
  return (
    <>
      <h1>Briefing</h1>
      <p className="page-lead">
        Kort, redigerbar visning af publicerede signaler og opportunities:
        vigtigste udviklinger, nye verificerede skandinaviske cases,
        teknologier i bevægelse og 3&#8211;5 næste skridt.
      </p>
      <EmptyState slice="Slice 6">
        Briefingen genereres fra publicerede signaler, når kæden er i drift.
      </EmptyState>
    </>
  );
}
