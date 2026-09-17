import Link from "next/link";
import {
  listOpportunities,
  listProblems,
  listSignals,
  type Opportunity,
  type Problem,
  type Signal,
} from "../lib/api";
import {
  CreateOpportunityForm,
  OpportunityActions,
  STATUS_LABELS,
} from "./OpportunityControls";

export const dynamic = "force-dynamic";

export default async function OpportunitiesPage() {
  let opportunities: Opportunity[] | null = null;
  let problems: Problem[] = [];
  let signals: Signal[] = [];
  try {
    const [oppPage, problemPage, signalPage] = await Promise.all([
      listOpportunities(),
      listProblems(),
      listSignals(),
    ]);
    opportunities = oppPage.items;
    problems = problemPage.items;
    signals = signalPage.items.filter((s) => s.status === "published");
  } catch {
    opportunities = null;
  }

  if (opportunities === null) {
    return (
      <>
        <h1>Opportunities</h1>
        <div className="alert-error" role="alert">
          API&#8217;et kunne ikke nås. Start backenden og genindlæs siden.
        </div>
      </>
    );
  }

  return (
    <>
      <h1>Opportunities</h1>
      <p className="page-lead">
        Ekstern udvikling &#215; dokumentation &#215; relevant OK-problem.
        AI Radar kvalificerer muligheder — business cases og projekter styres
        andetsteds. En kandidat kræver menneskelig godkendelse, før den kan
        rykke i pipelinen.
      </p>

      <CreateOpportunityForm problems={problems} signals={signals} />

      {opportunities.length === 0 ? (
        <div className="empty-state">
          <p>
            <strong>Ingen opportunities endnu.</strong>
          </p>
          <p>Opret den første kandidat ud fra et publiceret signal ovenfor.</p>
        </div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">Titel</th>
              <th scope="col">OK-problem</th>
              <th scope="col">Status</th>
              <th scope="col">Godkendt</th>
              <th scope="col">Evidens</th>
              <th scope="col">Handlinger</th>
            </tr>
          </thead>
          <tbody>
            {opportunities.map((opportunity) => (
              <tr key={opportunity.id}>
                <td>
                  <Link href={`/opportunities/${opportunity.id}`}>
                    {opportunity.title}
                  </Link>
                </td>
                <td>{opportunity.problem_name ?? "–"}</td>
                <td>
                  <span className="badge badge-muted">
                    {STATUS_LABELS[opportunity.status]}
                  </span>
                </td>
                <td>
                  {opportunity.approved ? (
                    <span className="badge badge-ok">Godkendt</span>
                  ) : (
                    <span className="badge badge-muted">Kandidat</span>
                  )}
                </td>
                <td>
                  {opportunity.signal_count} signaler ·{" "}
                  {opportunity.claim_count} claims
                </td>
                <td>
                  <OpportunityActions opportunity={opportunity} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
