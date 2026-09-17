import Link from "next/link";
import {
  listApprovedClaims,
  listSignals,
  type Claim,
  type Signal,
} from "../../lib/api";
import {
  DOCUMENTATION_LABELS,
  SIGNAL_STATUS_LABELS,
  formatDateTime,
} from "../../lib/labels";
import { CreateSignalForm, SignalRowActions } from "./SignalBuilder";

export const dynamic = "force-dynamic";

export default async function AdminSignalsPage() {
  let signals: Signal[] | null = null;
  let approvedClaims: Claim[] = [];
  try {
    const [signalPage, claimPage] = await Promise.all([
      listSignals(),
      listApprovedClaims(),
    ]);
    signals = signalPage.items;
    approvedClaims = claimPage.items;
  } catch {
    signals = null;
  }

  return (
    <>
      <h1>Signaler</h1>
      <p className="page-lead">
        Saml godkendte claims til publicerbar intelligence. Kun godkendte
        claims kan være faktagrundlag, og publicering er en menneskelig
        handling.
      </p>

      {signals === null ? (
        <div className="alert-error" role="alert">
          API&#8217;et kunne ikke nås, eller din rolle giver ikke adgang
          (kræver Reviewer eller Admin).
        </div>
      ) : (
        <>
          <CreateSignalForm approvedClaims={approvedClaims} />

          {signals.length === 0 ? (
            <div className="empty-state">
              <p>
                <strong>Ingen signaler endnu.</strong>
              </p>
              <p>Opret det første udkast ovenfor.</p>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Titel</th>
                  <th scope="col">Status</th>
                  <th scope="col">Dokumentation</th>
                  <th scope="col">Claims</th>
                  <th scope="col">Publiceret</th>
                  <th scope="col">Handlinger</th>
                </tr>
              </thead>
              <tbody>
                {signals.map((signal) => (
                  <tr key={signal.id}>
                    <td>
                      <Link href={`/signals/${signal.id}`}>{signal.title}</Link>
                    </td>
                    <td>
                      <span
                        className={
                          signal.status === "published"
                            ? "badge badge-ok"
                            : "badge badge-muted"
                        }
                      >
                        {SIGNAL_STATUS_LABELS[signal.status]}
                      </span>
                    </td>
                    <td>{DOCUMENTATION_LABELS[signal.documentation_level]}</td>
                    <td>{signal.claim_count}</td>
                    <td>{formatDateTime(signal.published_at)}</td>
                    <td>
                      <SignalRowActions signal={signal} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </>
  );
}
