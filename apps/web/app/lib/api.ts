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
