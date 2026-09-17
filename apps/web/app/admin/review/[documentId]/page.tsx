import Link from "next/link";
import {
  getDocument,
  type Claim,
  type DocumentReview,
  type ReviewStatus,
} from "../../../lib/api";
import { ClaimActions, DocumentControls } from "./ReviewControls";

export const dynamic = "force-dynamic";

const REVIEW_STATUS_LABELS: Record<ReviewStatus, string> = {
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

function statusBadgeClass(status: ReviewStatus): string {
  if (status === "approved" || status === "approved_with_edits")
    return "badge badge-ok";
  if (status === "rejected") return "badge badge-danger";
  return "badge badge-muted";
}

function ClaimCard({ claim }: { claim: Claim }) {
  return (
    <article className="claim-card">
      <header className="claim-card-header">
        <span className="badge badge-muted">
          {CLAIM_TYPE_LABELS[claim.claim_type]}
        </span>
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
        {claim.object_name ?? claim.object_text ?? (
          <i>Ikke dokumenteret</i>
        )}
      </p>
      {claim.evidence.map((evidence) => (
        <blockquote className="evidence-quote" key={evidence.id}>
          &#8220;{evidence.supporting_excerpt}&#8221;
        </blockquote>
      ))}
      {claim.possible_duplicate_ids.length > 0 ? (
        <p className="cell-sub">
          Mulig dublet af {claim.possible_duplicate_ids.length} andet/andre
          claim(s) — vurdér relationen ved godkendelse.
        </p>
      ) : null}
      <ClaimActions claim={claim} />
    </article>
  );
}

export default async function ReviewDocumentPage({
  params,
}: {
  params: Promise<{ documentId: string }>;
}) {
  const { documentId } = await params;
  let doc: DocumentReview | null = null;
  try {
    doc = await getDocument(documentId);
  } catch {
    doc = null;
  }

  if (doc === null) {
    return (
      <>
        <h1>Review</h1>
        <div className="alert-error" role="alert">
          Dokumentet kunne ikke hentes. Kontrollér at API&#8217;et kører, og at
          din rolle giver adgang.
        </div>
        <p>
          <Link href="/admin/review">Tilbage til dokumentlisten</Link>
        </p>
      </>
    );
  }

  return (
    <>
      <p className="cell-sub">
        <Link href="/admin/review">← Dokumentliste</Link>
      </p>
      <h1>{doc.title ?? "(uden titel)"}</h1>
      <p className="page-lead">
        Status: {doc.processing_status} · MIME: {doc.mime_type ?? "–"}
        {doc.canonical_url ? <> · Kilde-URL: {doc.canonical_url}</> : null}
        {doc.raw_url ? (
          <>
            {" "}
            · <a href={doc.raw_url}>Original fil</a>
          </>
        ) : null}
      </p>

      <DocumentControls document={doc} />

      {doc.claims.length === 0 ? (
        <div className="empty-state">
          <p>
            <strong>Ingen foreslåede claims.</strong>
          </p>
          <p>
            Kør AI-behandling for at få relevans og claim-forslag med
            evidensuddrag.
          </p>
        </div>
      ) : (
        <section aria-label="Foreslåede claims" className="claim-list">
          {doc.claims.map((claim) => (
            <ClaimCard key={claim.id} claim={claim} />
          ))}
        </section>
      )}

      {doc.normalized_text ? (
        <details className="card">
          <summary>Normaliseret tekst</summary>
          <pre className="document-text">{doc.normalized_text}</pre>
        </details>
      ) : null}
    </>
  );
}
