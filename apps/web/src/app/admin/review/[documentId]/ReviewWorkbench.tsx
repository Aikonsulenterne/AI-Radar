"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { Claim, DocumentReview, Evidence } from "../../../lib/api";
import { ClaimActions } from "./ReviewControls";

const REVIEW_STATUS_LABELS: Record<Claim["review_status"], string> = {
  proposed: "Foreslået",
  approved: "Godkendt",
  approved_with_edits: "Godkendt med rettelser",
  needs_corroboration: "Kræver yderligere dokumentation",
  rejected: "Afvist",
};

const CLAIM_TYPE_LABELS: Record<Claim["claim_type"], string> = {
  adoption: "Adoption",
  use_case: "Use case",
  stage: "Stadie",
  technology_vendor: "Teknologi/leverandør",
  effect: "Effekt",
  negative: "Barriere/negativt",
  organization: "Organisation",
};

const ENTITY_LABELS: Record<"company" | "technology" | "vendor", string> = {
  company: "Virksomhed",
  technology: "Teknologi",
  vendor: "Leverandør",
};

function statusBadgeClass(status: Claim["review_status"]): string {
  if (status === "approved" || status === "approved_with_edits")
    return "badge badge-ok";
  if (status === "rejected") return "badge badge-danger";
  if (status === "needs_corroboration") return "badge badge-warn";
  return "badge badge-muted";
}

type Span = { start: number; end: number; claimId: string };

/**
 * Evidensuddragenes placering i teksten. Offsets beregnes server-side; passer
 * de ikke, findes uddraget ordret. Uddrag der ikke kan placeres, fremhæves
 * ikke — de vises fortsat på claim-kortet, så intet evidensuddrag går tabt.
 */
function evidenceSpans(text: string, claims: Claim[]): Span[] {
  const spans: Span[] = [];
  for (const claim of claims) {
    for (const evidence of claim.evidence) {
      let start = evidence.excerpt_start;
      let end = evidence.excerpt_end;
      if (
        start === null ||
        end === null ||
        text.slice(start, end) !== evidence.supporting_excerpt
      ) {
        const found = text.indexOf(evidence.supporting_excerpt);
        if (found === -1) continue;
        start = found;
        end = found + evidence.supporting_excerpt.length;
      }
      spans.push({ start, end, claimId: claim.id });
    }
  }
  spans.sort((a, b) => a.start - b.start);

  // Overlappende uddrag: behold det første, så teksten aldrig dubleres.
  const placed: Span[] = [];
  let cursor = 0;
  for (const span of spans) {
    if (span.start >= cursor) {
      placed.push(span);
      cursor = span.end;
    }
  }
  return placed;
}

function DocumentPane({
  text,
  claims,
  selectedClaimId,
}: {
  text: string;
  claims: Claim[];
  selectedClaimId: string | null;
}) {
  const spans = useMemo(() => evidenceSpans(text, claims), [text, claims]);
  const container = useRef<HTMLPreElement>(null);

  useEffect(() => {
    const active = container.current?.querySelector(".evidence-mark-active");
    if (!active) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    active.scrollIntoView({ block: "center", behavior: reduced ? "auto" : "smooth" });
  }, [selectedClaimId]);

  const parts: React.ReactNode[] = [];
  let cursor = 0;
  spans.forEach((span, index) => {
    if (span.start > cursor) parts.push(text.slice(cursor, span.start));
    const active = span.claimId === selectedClaimId;
    parts.push(
      <mark
        key={`${span.claimId}-${index}`}
        className={active ? "evidence-mark evidence-mark-active" : "evidence-mark"}
      >
        {text.slice(span.start, span.end)}
      </mark>,
    );
    cursor = span.end;
  });
  if (cursor < text.length) parts.push(text.slice(cursor));

  return (
    <pre className="document-text" ref={container}>
      {parts}
    </pre>
  );
}

function ClaimCard({
  claim,
  selected,
  onShowInText,
}: {
  claim: Claim;
  selected: boolean;
  onShowInText: () => void;
}) {
  // UI Master §15: godkendelse må ikke ske uden synligt evidensuddrag.
  const hasEvidence = claim.evidence.length > 0;

  return (
    <article
      className={selected ? "claim-card claim-card-selected" : "claim-card"}
      aria-current={selected ? "true" : undefined}
    >
      <header className="claim-card-header">
        <span className="badge badge-muted">{CLAIM_TYPE_LABELS[claim.claim_type]}</span>
        <span className={statusBadgeClass(claim.review_status)}>
          {REVIEW_STATUS_LABELS[claim.review_status]}
        </span>
        <span className="cell-sub">
          {claim.created_by === "ai" ? "Foreslået af AI" : "Oprettet af menneske"}
        </span>
      </header>

      <p className="claim-statement">
        <b>{claim.subject_name ?? "(ukendt subjekt)"}</b>{" "}
        <span className="claim-predicate">{claim.predicate}</span>{" "}
        {claim.object_name ?? claim.object_text ?? <i>Ikke dokumenteret</i>}
      </p>

      <p className="cell-sub">
        Subjekt: {ENTITY_LABELS[claim.subject_entity_type]}
        {claim.object_entity_type
          ? ` · Objekt: ${ENTITY_LABELS[claim.object_entity_type]}`
          : claim.object_text
            ? " · Objekt: fritekst, ingen matchet entity"
            : ""}
      </p>

      {hasEvidence ? (
        <>
          {claim.evidence.map((evidence: Evidence) => (
            <blockquote className="evidence-quote" key={evidence.id}>
              &#8220;{evidence.supporting_excerpt}&#8221;
            </blockquote>
          ))}
          <button type="button" className="btn-link" onClick={onShowInText}>
            Vis uddraget i dokumentet
          </button>
        </>
      ) : (
        <p className="alert-error" role="note">
          Intet evidensuddrag — claimet kan ikke godkendes.
        </p>
      )}

      {claim.possible_duplicate_ids.length > 0 ? (
        <p className="cell-sub">
          Mulig dublet af {claim.possible_duplicate_ids.length} andet/andre claim(s) — vurdér
          relationen ved godkendelse.
        </p>
      ) : null}

      {hasEvidence ? <ClaimActions claim={claim} /> : null}
    </article>
  );
}

export function ReviewWorkbench({ document }: { document: DocumentReview }) {
  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(null);
  const text = document.normalized_text ?? "";

  return (
    <div className="review-panes">
      <section className="review-pane" aria-label="Dokument med evidensuddrag">
        <h2 className="section-title">
          Dokument{" "}
          {text ? <span className="section-tag">Evidensuddrag fremhævet</span> : null}
        </h2>
        {text ? (
          <DocumentPane
            text={text}
            claims={document.claims}
            selectedClaimId={selectedClaimId}
          />
        ) : (
          <div className="empty-state">
            <p>
              <strong>Ingen normaliseret tekst.</strong>
            </p>
            <p>
              Formatet kunne ikke udtrækkes. Uden tekst kan der ikke udtrækkes claims med
              ordrette evidensuddrag.
            </p>
          </div>
        )}
      </section>

      <section className="review-pane" aria-label="Foreslåede claims og reviewhandlinger">
        <h2 className="section-title">Foreslåede claims ({document.claims.length})</h2>
        {document.claims.length === 0 ? (
          <div className="empty-state">
            <p>
              <strong>Ingen foreslåede claims.</strong>
            </p>
            <p>Kør AI-behandling for at få claim-forslag med ordrette evidensuddrag.</p>
          </div>
        ) : (
          <div className="claim-list">
            {document.claims.map((claim) => (
              <ClaimCard
                key={claim.id}
                claim={claim}
                selected={claim.id === selectedClaimId}
                onShowInText={() => setSelectedClaimId(claim.id)}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
