import Link from "next/link";
import {
  getDecisionBrief,
  getOpportunityMap,
  listInternalSignals,
  type DecisionBriefData,
  type ProblemOpportunity,
  type Signal,
} from "../lib/api";
import { formatDateTime } from "../lib/labels";
import { ApiErrorAlert } from "../../components/states/api-error";
import { PrintButton } from "./PrintButton";

export const dynamic = "force-dynamic";

const kr = new Intl.NumberFormat("da-DK", { maximumFractionDigits: 0 });

function amount(value: number | null, suffix = " kr."): string {
  return value === null ? "–" : `${kr.format(value)}${suffix}`;
}

function Missing({ children }: { children: React.ReactNode }) {
  return <span className="brief-missing">{children}</span>;
}

export default async function DecisionBriefPage() {
  let data: DecisionBriefData | null = null;
  let problems: ProblemOpportunity[] = [];
  let internal: Signal[] = [];
  let loadError: unknown = null;
  try {
    const [brief, map, internalPage] = await Promise.all([
      getDecisionBrief(),
      getOpportunityMap(),
      listInternalSignals(),
    ]);
    data = brief;
    problems = map.problems.filter(
      (p) => p.vendors.length > 0 || p.references.length > 0,
    );
    internal = internalPage.items;
  } catch (error) {
    loadError = error;
  }

  if (data === null) {
    return (
      <>
        <h1>Beslutningsoplæg</h1>
        <ApiErrorAlert error={loadError} />
      </>
    );
  }

  const { brief, calculation: calc } = data;
  const top = problems.slice(0, 3);
  const peers = Array.from(
    new Map(
      problems.flatMap((p) => p.references).map((r) => [r.name, r]),
    ).values(),
  ).slice(0, 6);
  const effects = Array.from(
    new Map(
      problems
        .flatMap((p) => p.effects)
        .map((e) => [`${e.organization}|${e.effect}`, e]),
    ).values(),
  ).slice(0, 4);

  return (
    <>
      <div className="no-print" style={{ marginBottom: "16px" }}>
        <PrintButton />{" "}
        <Link href="/admin/beslutningsoplaeg">Redigér OK-tal og oplæg →</Link>
      </div>

      <article className="brief" aria-label="Beslutningsoplæg">
        <p className="hero-eyebrow" style={{ color: "var(--ok-red)" }}>
          Beslutningsoplæg · OK Kundeservice
        </p>
        <h1>{brief.title}</h1>
        <p className="cell-sub">
          Opdateret {formatDateTime(data.updated_at)}. Fakta stammer fra AI
          Radarens kilder; leverandørers egne tal er markeret. Tal om OK er
          indtastet manuelt.
        </p>

        <h2>Udgangspunkt — OK Kundeservice i dag</h2>
        <div className="brief-figures">
          <div className="brief-figure">
            <strong>
              {calc.total_contacts === null
                ? "–"
                : kr.format(calc.total_contacts)}
            </strong>
            henvendelser pr. år
          </div>
          <div className="brief-figure">
            <strong>{brief.fte ?? "–"}</strong>
            årsværk
          </div>
          <div className="brief-figure">
            <strong>{amount(calc.cost_per_contact)}</strong>
            pr. henvendelse
          </div>
          <div className="brief-figure">
            <strong>
              {brief.aht_minutes === null ? "–" : `${brief.aht_minutes} min`}
            </strong>
            gns. behandlingstid
          </div>
        </div>
        <p className="cell-sub">
          Kontaktcentersystem:{" "}
          {brief.contact_center_system ?? <Missing>ikke udfyldt</Missing>}
          {brief.contract_renewal
            ? ` · kontrakt udløber ${brief.contract_renewal}`
            : ""}
        </p>

        <h2>
          Det har vi fundet i egne data{" "}
          <Link href="/indsigter" className="no-print">
            (Indsigter →)
          </Link>
        </h2>
        {brief.internal_findings.length === 0 && internal.length === 0 ? (
          <p>
            <Missing>Ingen interne fund indtastet endnu.</Missing>
          </p>
        ) : (
          <ul>
            {brief.internal_findings.map((finding) => (
              <li key={finding.title}>
                <strong>{finding.title}</strong>
                {finding.figure ? ` — ${finding.figure}` : ""}
                {finding.description ? `. ${finding.description}` : ""}
              </li>
            ))}
            {internal.map((signal) => (
              <li key={signal.id}>
                <Link href={`/signals/${signal.id}`}>{signal.title}</Link>{" "}
                <span className="cell-sub">(intern analyse)</span>
              </li>
            ))}
          </ul>
        )}

        <h2>Det tilbyder markedet — til netop vores udfordringer</h2>
        {top.length === 0 ? (
          <p>
            <Missing>Radaren har endnu ingen dokumenterede tilbud.</Missing>
          </p>
        ) : (
          <ul>
            {top.map((problem) => (
              <li key={problem.problem_id}>
                <strong>{problem.name}:</strong>{" "}
                {problem.capabilities.map((c) => c.name).join(", ")}
                {problem.vendors.length > 0
                  ? ` — fx ${problem.vendors
                      .slice(0, 3)
                      .map((v) => v.name)
                      .join(", ")}`
                  : ""}
              </li>
            ))}
          </ul>
        )}

        <h2>Det har andre gjort</h2>
        {peers.length === 0 && effects.length === 0 ? (
          <p>
            <Missing>Ingen dokumenterede referencer endnu.</Missing>
          </p>
        ) : (
          <ul>
            {effects.map((effect) => (
              <li key={`${effect.organization}-${effect.effect}`}>
                <strong>{effect.organization}:</strong> {effect.effect}
                {effect.vendor_source ? (
                  <span className="cell-sub"> (leverandørens egne tal)</span>
                ) : null}
              </li>
            ))}
            {peers
              .filter((p) => !effects.some((e) => e.organization === p.name))
              .map((peer) => (
                <li key={peer.name}>
                  <strong>{peer.name}:</strong> {peer.how}
                </li>
              ))}
          </ul>
        )}
        {brief.peer_calls.length > 0 ? (
          <p className="cell-sub">
            Samtaler med branchekolleger:{" "}
            {brief.peer_calls
              .map(
                (c) => `${c.organization}${c.status ? ` (${c.status})` : ""}`,
              )
              .join(", ")}
          </p>
        ) : null}

        <h2>Hvad er det værd for OK? — regneeksempel</h2>
        {calc.saving_low === null || calc.saving_high === null ? (
          <p>
            <Missing>
              Mangler: {calc.missing.join(", ")}. Udfyld under Admin → OK-tal
              &amp; oplæg.
            </Missing>
          </p>
        ) : (
          <p>
            Kundeservice koster ca. <strong>{amount(calc.annual_cost)}</strong>{" "}
            om året. Hvis AI fjerner eller forkorter {brief.scenario_low_pct}–
            {brief.scenario_high_pct} % af arbejdet, svarer det til{" "}
            <strong>{amount(calc.saving_low)}</strong> –{" "}
            <strong>{amount(calc.saving_high)}</strong> om året
            {calc.handling_hours !== null
              ? ` (af ca. ${kr.format(calc.handling_hours)} behandlingstimer)`
              : ""}
            .{" "}
            <span className="cell-sub">
              Antagelser, ikke dokumenterede effekter for OK — skal efterprøves
              i piloten.
            </span>
          </p>
        )}

        <h2>Det beder jeg om</h2>
        <div className="brief-ask">
          <p>{brief.ask ?? <Missing>Ønsket er ikke udfyldt.</Missing>}</p>
          {brief.kill_criterion ? (
            <p>
              <strong>Stopkriterium:</strong> {brief.kill_criterion}
            </p>
          ) : null}
          {brief.data_promise ? (
            <p>
              <strong>Data:</strong> {brief.data_promise}
            </p>
          ) : null}
          {brief.budget_deadline ? (
            <p>
              <strong>Hvorfor nu:</strong> budgetfrist {brief.budget_deadline}
              {brief.contract_renewal
                ? `, kontraktfornyelse ${brief.contract_renewal}`
                : ""}
              .
            </p>
          ) : null}
        </div>

        <p className="cell-sub" style={{ marginTop: "24px" }}>
          Radaren holder billedet opdateret automatisk hver uge:{" "}
          <Link href="/muligheder">Muligheder</Link> ·{" "}
          <Link href="/vendors">Leverandører</Link>.
        </p>
      </article>
    </>
  );
}
