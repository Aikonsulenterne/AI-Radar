"""AI-foreslåede opportunity-kandidater (Product Master §10).

Ekstern udvikling × dokumentation × relevant OK-problem. Faktagrundlaget er
signalets allerede godkendte claims — modellen får intet andet og må intet
tilføje. Resultatet er en ugodkendt kandidat: et menneske godkender, før
status kan rykkes (samme flow som menneskeskabte kandidater).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.prompts import (
    OPPORTUNITY_PROMPT_ID,
    OPPORTUNITY_PROMPT_VERSION,
    OPPORTUNITY_SYSTEM,
)
from app.ai.provider import AIProvider
from app.ai.schemas import OpportunityProposalResult, call_with_schema
from app.enums import ReviewStatus
from app.errors import ApiError
from app.models_claims import Claim
from app.models_opportunities import (
    Opportunity,
    OpportunityClaim,
    OpportunitySignal,
    ProblemTaxonomy,
)
from app.models_signals import Signal, SignalClaim
from app.pipeline.entities import entity_name, normalize_alias

_APPROVED = {ReviewStatus.approved, ReviewStatus.approved_with_edits}


def approved_claims_for_signal(db: Session, signal: Signal) -> list[Claim]:
    claim_ids = db.scalars(
        select(SignalClaim.claim_id).where(SignalClaim.signal_id == signal.id)
    ).all()
    claims = [claim for cid in claim_ids if (claim := db.get(Claim, cid)) is not None]
    return [claim for claim in claims if claim.review_status in _APPROVED]


def _claim_line(db: Session, claim: Claim) -> str:
    subject = entity_name(db, claim.subject_entity_type, claim.subject_entity_id) or "Ukendt"
    obj = entity_name(db, claim.object_entity_type, claim.object_entity_id) or claim.object_text
    return f"- {subject} | {claim.predicate.value} | {obj or 'ikke angivet'}"


def _user_prompt(db: Session, signal: Signal, claims: list[Claim], problems: list[str]) -> str:
    facts = "\n".join(_claim_line(db, claim) for claim in claims)
    problem_list = "\n".join(f"- {name}" for name in problems)
    return (
        f"SIGNAL: {signal.title}\n\n"
        f"APPROVED FACTS (the only factual basis):\n{facts}\n\n"
        f"OK PROBLEM LIST (choose exactly one name, verbatim):\n{problem_list}\n"
    )


def propose_opportunity(db: Session, provider: AIProvider, signal: Signal) -> Opportunity:
    """Foreslår én kandidat ud fra et signals godkendte claims."""
    claims = approved_claims_for_signal(db, signal)
    if not claims:
        raise ApiError(
            409,
            "no_approved_claims",
            "Signalet har ingen godkendte claims at bygge et forslag på.",
        )

    problems = list(
        db.scalars(
            select(ProblemTaxonomy)
            .where(ProblemTaxonomy.active.is_(True))
            .order_by(ProblemTaxonomy.name)
        ).all()
    )
    if not problems:
        raise ApiError(409, "empty_taxonomy", "Problem-taxonomien er tom.")

    result = call_with_schema(
        provider,
        prompt_id=OPPORTUNITY_PROMPT_ID,
        prompt_version=OPPORTUNITY_PROMPT_VERSION,
        system=OPPORTUNITY_SYSTEM,
        user=_user_prompt(db, signal, claims, [problem.name for problem in problems]),
        result_model=OpportunityProposalResult,
    )

    if result.proposal is None:
        # At afvise er et gyldigt svar — der opfindes ikke en kobling.
        raise ApiError(
            409,
            "no_opportunity",
            result.reason or "Modellen fandt ingen relevant kobling til et OK-problem.",
        )

    proposal = result.proposal
    wanted = normalize_alias(proposal.problem_name)
    problem = next((p for p in problems if normalize_alias(p.name) == wanted), None)
    if problem is None:
        # Taxonomien er kurateret: et ukendt problemnavn oprettes ikke.
        raise ApiError(
            502,
            "unknown_problem",
            f"Forslaget pegede på et ukendt OK-problem ({proposal.problem_name}).",
        )

    opportunity = Opportunity(
        title=proposal.title,
        problem_id=problem.id,
        relevance_hypothesis=proposal.relevance_hypothesis,
        evidence_gaps=proposal.evidence_gaps,
        recommended_next_action=proposal.recommended_next_action,
        proposed_by_ai=True,
        proposal_prompt_version=OPPORTUNITY_PROMPT_VERSION,
    )
    db.add(opportunity)
    db.flush()

    db.add(OpportunitySignal(opportunity_id=opportunity.id, signal_id=signal.id))
    for claim in claims:
        db.add(OpportunityClaim(opportunity_id=opportunity.id, claim_id=claim.id))
    db.flush()
    return opportunity
