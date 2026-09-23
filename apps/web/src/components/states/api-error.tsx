import Link from "next/link";
import { ApiClientError } from "../../app/lib/api";

/**
 * Fejlstatus for en side, der ikke kunne hente sine data. Skelner mellem
 * manglende login, manglende rolle og et API, der ikke svarer — de kræver
 * tre forskellige handlinger af brugeren.
 */
export function ApiErrorAlert({
  error,
  requiredRole,
}: {
  error: unknown;
  requiredRole?: "Reviewer eller Admin";
}) {
  if (error instanceof ApiClientError && error.status === 401) {
    return (
      <div className="alert-error" role="alert">
        Du er ikke logget ind. <Link href="/login">Log ind</Link> for at se
        indholdet.
      </div>
    );
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
