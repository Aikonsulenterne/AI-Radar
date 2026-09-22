import Link from "next/link";
import { getOpportunity, type OpportunityDetail } from "../../lib/api";
import { OpportunityActions, STATUS_LABELS } from "../OpportunityControls";

export const dynamic = "force-dynamic";

export default async function OpportunityPage({
  params,
}: {
  params: Promise<{ opportunityId: string }>;
}) {
  const { opportunityId } = await params;
  let opportunity: OpportunityDetail | null = null;
  try {
    opportunity = await getOpportunity(opportunityId);
  } catch {
    opportunity = null;
  }

  if (opportunity === null) {
    return (
      <>
        <h1>Opportunity</h1>
        <div className="alert-error" role="alert">
          Opportunity&#8217;en kunne ikke hentes.
        </div>
        <p>
          <Link href="/opportunities">Tilbage til Opportunities</Link>
        </p>
      </>
    );
  }

  return (
    <>
      <p className="cell-sub">
        <Link href="/opportunities">← Opportunities</Link>
      </p>
      <h1>{opportunity.title}</h1>
      <p className="page-lead">
        OK-problem: {opportunity.problem_name ?? "–"} · Status:{" "}
        {STATUS_LABELS[opportunity.status]} ·{" "}
        {opportunity.approved ? "Godkendt" : "Kandidat — afventer godkendelse"}
      </p>

      {opportunity.proposed_by_ai ? (
        <div className="ai-proposal-notice" role="note">
          <span className="badge badge-ai">AI-forslag</span>
          <p>
            Hypotese, evidenshuller og næste handling er foreslået af AI ud fra
            de godkendte claims nedenfor — ikke skrevet af et menneske. Intet i
            forslaget er nye fakta. Godkend først, når du har vurderet det.
            {opportunity.proposal_prompt_version
              ? ` Promptversion ${opportunity.proposal_prompt_version}.`
              : ""}
          </p>
        </div>
      ) : null}

      <OpportunityActions opportunity={opportunity} />

      <section className="signal-section signal-analysis" aria-label="Hypotese">
        <h2 className="section-title">
          Relevanshypotese{" "}
          <span className="section-tag">Analyse, ikke fakta</span>
        </h2>
        <p>{opportunity.relevance_hypothesis}</p>
        {opportunity.evidence_gaps ? (
          <p className="cell-sub">
            Evidenshuller: {opportunity.evidence_gaps}
          </p>
        ) : null}
      </section>

      <section
        className="signal-section signal-recommendation"
        aria-label="Næste handling"
      >
        <h2 className="section-title">
          Anbefalet næste handling{" "}
          <span className="section-tag">Anbefaling</span>
        </h2>
        <p>{opportunity.recommended_next_action}</p>
      </section>

      <section
        className="signal-section section-fact"
        aria-label="Ekstern evidens"
      >
        <h2 className="section-title">
          Ekstern evidens{" "}
          <span className="section-tag">Dokumenteret fakta</span>
        </h2>
        {opportunity.signals.length === 0 &&
        opportunity.claims.length === 0 ? (
          <p className="cell-sub">
            Ingen evidens tilknyttet endnu — kobl signaler eller claims til
            kandidaten.
          </p>
        ) : (
          <>
            {opportunity.signals.length > 0 ? (
              <ul>
                {opportunity.signals.map((signal) => (
                  <li key={signal.id}>
                    <Link href={`/signals/${signal.id}`}>{signal.title}</Link>{" "}
                    <span className="cell-sub">({signal.status})</span>
                  </li>
                ))}
              </ul>
            ) : null}
            {opportunity.claims.length > 0 ? (
              <div className="claim-list">
                {opportunity.claims.map((claim) => (
                  <article className="claim-card" key={claim.id}>
                    <p className="claim-statement">
                      <b>{claim.subject_name ?? "(ukendt)"}</b>{" "}
                      <span className="claim-predicate">{claim.predicate}</span>{" "}
                      {claim.object_name ?? claim.object_text ?? ""}
                    </p>
                    {claim.evidence.map((evidence) => (
                      <blockquote className="evidence-quote" key={evidence.id}>
                        &#8220;{evidence.supporting_excerpt}&#8221;
                      </blockquote>
                    ))}
                  </article>
                ))}
              </div>
            ) : null}
          </>
        )}
      </section>
    </>
  );
}
