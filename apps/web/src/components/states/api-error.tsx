import { ApiClientError } from "../../app/lib/api";
import { SessionRecovery } from "../auth/session-recovery";

/**
 * Fejlstatus for en side, der ikke kunne hente sine data. Skelner mellem
 * manglende login, manglende rolle og et API, der ikke svarer — de kræver
 * tre forskellige handlinger af brugeren.
 */
export function ApiErrorAlert({
  error,
  requiredRole,
  notFound,
}: {
  error: unknown;
  requiredRole?: "Reviewer eller Admin";
  /** Tekst ved 404 — fx at elementet er arkiveret eller ikke publiceret. */
  notFound?: string;
}) {
  if (notFound && error instanceof ApiClientError && error.status === 404) {
    return (
      <div className="alert-error" role="alert">
        {notFound}
      </div>
    );
  }
  if (error instanceof ApiClientError && error.status === 401) {
    return <SessionRecovery />;
  }
  if (error instanceof ApiClientError && error.status === 403) {
    return (
      <div className="alert-error" role="alert">
        Din rolle giver ikke adgang til denne side
        {requiredRole ? ` (kræver ${requiredRole})` : ""}. Kontakt en
        administrator.
      </div>
    );
  }
  if (error instanceof ApiClientError) {
    return (
      <div className="alert-error" role="alert">
        API&#8217;et svarede med en fejl ({error.status}): {error.message}
      </div>
    );
  }
  return (
    <div className="alert-error" role="alert">
      API&#8217;et kunne ikke nås. Backenden kan være ved at starte op efter
      inaktivitet — vent et minut og genindlæs siden.
    </div>
  );
}
