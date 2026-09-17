/**
 * Typed data access layer mod FastAPI (Technical Master §12).
 * Ingen direkte databaseadgang fra frontend — alt går via /api/v1.
 *
 * Auth: I lokal udvikling kører API'et med dev-bypass. Supabase Auth-session
 * og Bearer-token vedhæftes, når auth-wiring kommer i en senere slice.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export type SourceType =
  | "primary"
  | "independent_analysis"
  | "vendor_case"
  | "vendor_claim"
  | "media"
  | "research"
  | "early_signal";

export type RetrievalMethod = "rss" | "web_fetch" | "manual_upload";
export type Frequency = "manual" | "daily" | "weekly" | "monthly";
export type AccessClass = "public" | "licensed" | "restricted";

export type ProcessingStatus =
  | "discovered"
  | "fetched"
  | "normalized"
  | "classified_relevant"
  | "classified_irrelevant"
  | "extraction_pending"
  | "review_pending"
  | "partially_reviewed"
  | "reviewed"
  | "failed";

export interface Source {
  id: string;
  name: string;
  base_url: string | null;
  source_type: SourceType;
  retrieval_method: RetrievalMethod;
  endpoint_url: string | null;
  country_code: string | null;
  frequency: Frequency;
  access_class: AccessClass;
  active: boolean;
  last_checked_at: string | null;
  next_check_at: string | null;
  owner_user_id: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentRow {
  id: string;
  source_id: string;
  canonical_url: string | null;
  title: string | null;
  language_code: string | null;
  published_at: string | null;
  retrieved_at: string;
  content_hash: string;
  mime_type: string | null;
  processing_status: ProcessingStatus;
  is_demo: boolean;
  error_code: string | null;
  created_at: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface SourceCreateInput {
  name: string;
  source_type: SourceType;
  retrieval_method: RetrievalMethod;
  access_class: AccessClass;
  base_url?: string | null;
  endpoint_url?: string | null;
  country_code?: string | null;
  frequency?: Frequency;
  notes?: string | null;
  active?: boolean;
}

export interface RunResult {
  source_id: string;
  document: DocumentRow;
  created: boolean;
}

export interface IngestOutcome {
  document: DocumentRow;
  created: boolean;
}

export class ApiClientError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    ...init,
  });
  if (!response.ok) {
    let code = "http_error";
    let message = `HTTP ${response.status}`;
    try {
      const body = (await response.json()) as {
        error?: { code?: string; message?: string };
      };
      code = body.error?.code ?? code;
      message = body.error?.message ?? message;
    } catch {
      // Ikke-JSON fejlsvar: behold statusbaseret besked.
    }
    throw new ApiClientError(response.status, code, message);
  }
  return (await response.json()) as T;
}

export function listSources(): Promise<Paginated<Source>> {
  return request<Paginated<Source>>("/sources?limit=200");
}

export function createSource(input: SourceCreateInput): Promise<Source> {
  return request<Source>("/sources", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function runSource(sourceId: string): Promise<RunResult> {
  return request<RunResult>(`/sources/${sourceId}/run`, { method: "POST" });
}

export function uploadDocument(
  sourceId: string,
  file: File,
  title?: string,
): Promise<IngestOutcome> {
  const form = new FormData();
  form.append("file", file);
  if (title) form.append("title", title);
  return request<IngestOutcome>(`/sources/${sourceId}/documents`, {
    method: "POST",
    body: form,
  });
}

export function listDocuments(): Promise<Paginated<DocumentRow>> {
  return request<Paginated<DocumentRow>>("/review/documents?limit=100");
}

export type ClaimType =
  | "adoption"
  | "use_case"
  | "stage"
  | "technology_vendor"
  | "effect"
  | "negative"
  | "organization";

export type ReviewStatus =
  | "proposed"
  | "approved"
  | "approved_with_edits"
  | "needs_corroboration"
  | "rejected";

export interface Evidence {
  id: string;
  document_id: string;
  supporting_excerpt: string;
  excerpt_start: number | null;
  excerpt_end: number | null;
  relationship: "supports" | "contradicts" | "supersedes";
  source_type_snapshot: SourceType | null;
  review_status: ReviewStatus;
}

export interface Claim {
  id: string;
  claim_type: ClaimType;
  predicate: string;
  subject_entity_type: "company" | "technology" | "vendor";
  subject_entity_id: string;
  subject_name: string | null;
  object_entity_type: "company" | "technology" | "vendor" | null;
  object_entity_id: string | null;
  object_name: string | null;
  object_text: string | null;
  normalized_value: Record<string, unknown> | null;
  valid_from: string | null;
  valid_to: string | null;
  observed_at: string;
  review_status: ReviewStatus;
  lifecycle_status: "current" | "contradicted" | "superseded" | "expired";
  created_by: "ai" | "human";
  reviewed_at: string | null;
  evidence: Evidence[];
  possible_duplicate_ids: string[];
}

export interface DocumentReview extends DocumentRow {
  normalized_text: string | null;
  raw_storage_path: string | null;
  raw_url: string | null;
  claims: Claim[];
}

export interface ProcessResult {
  document_id: string;
  status: ProcessingStatus;
  claims_created: number;
  claims_skipped: number;
  skipped_reasons: string[];
}

export function getDocument(documentId: string): Promise<DocumentReview> {
  return request<DocumentReview>(`/review/documents/${documentId}`);
}

export function processDocument(documentId: string): Promise<ProcessResult> {
  return request<ProcessResult>(`/review/documents/${documentId}/process`, {
    method: "POST",
  });
}

export function completeReview(documentId: string): Promise<DocumentRow> {
  return request<DocumentRow>(`/review/documents/${documentId}/complete`, {
    method: "POST",
  });
}

export function approveClaim(
  claimId: string,
  edits?: { object_text?: string | null },
): Promise<Claim> {
  return request<Claim>(`/review/claims/${claimId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(edits ? { edits } : {}),
  });
}

export function rejectClaim(claimId: string): Promise<Claim> {
  return request<Claim>(`/review/claims/${claimId}/reject`, {
    method: "POST",
  });
}

export function listApprovedClaims(): Promise<Paginated<Claim>> {
  return request<Paginated<Claim>>(
    "/review/claims?review_status=approved&limit=200",
  );
}

export type DocumentationLevel = "strong" | "limited" | "early" | "conflicting";
export type SignalStatus = "draft" | "published" | "archived";

export interface Signal {
  id: string;
  title: string;
  summary: string;
  analysis: string | null;
  recommendation: string | null;
  documentation_level: DocumentationLevel;
  status: SignalStatus;
  published_at: string | null;
  created_at: string;
  updated_at: string;
  claim_count: number;
}

export interface SignalDetail extends Signal {
  claims: Claim[];
  companies: { id: string; name: string }[];
  technologies: { id: string; name: string }[];
}

export interface Dashboard {
  published_signals: number;
  approved_claims: number;
  companies_with_claims: number;
  documents_in_review: number;
  technologies_by_horizon: { now: number; next: number; horizon: number };
  latest_signals: Signal[];
}

export interface SignalCreateInput {
  title: string;
  summary: string;
  analysis?: string | null;
  recommendation?: string | null;
  documentation_level: DocumentationLevel;
  claim_ids: string[];
}

export function getDashboard(): Promise<Dashboard> {
  return request<Dashboard>("/dashboard");
}

export function listSignals(status?: SignalStatus): Promise<Paginated<Signal>> {
  const query = status ? `?status=${status}` : "";
  return request<Paginated<Signal>>(`/signals${query}`);
}

export function getSignal(signalId: string): Promise<SignalDetail> {
  return request<SignalDetail>(`/signals/${signalId}`);
}

export function createSignal(input: SignalCreateInput): Promise<Signal> {
  return request<Signal>("/signals", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function publishSignal(signalId: string): Promise<Signal> {
  return request<Signal>(`/signals/${signalId}/publish`, { method: "POST" });
}

export function archiveSignal(signalId: string): Promise<Signal> {
  return request<Signal>(`/signals/${signalId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status: "archived" }),
  });
}
