import type { OkGain } from "../../app/lib/api";

/** Hvad andre fik ud af teknologien. Spændet beregnes af serveren ud fra
 * casene; leverandørens egne tal mærkes. */
export function GainLine({
  gain,
  prefix = "Andre fik",
  withSource = true,
}: {
  gain: OkGain | null;
  prefix?: string;
  /** Falsk inde i en knap (ingen link i link). */
  withSource?: boolean;
}) {
  if (!gain) {
    return <span className="gain gain-none">Effekt ikke oplyst i casene</span>;
  }
  const cases = gain.cases === 1 ? "1 case" : `${gain.cases} cases`;
  const detail = gain.vendor_only
    ? `${cases} · Leverandørens tal`
    : gain.independent === gain.cases
      ? cases
      : `${cases}, heraf ${gain.independent} uafhængig${gain.independent === 1 ? "" : "e"}`;
  return (
    <span className="gain">
      <span className="gain-label">{prefix}:</span> <strong>{gain.text}</strong>
      {gain.kpi ? ` (${gain.kpi})` : ""} <span className="muted">· {detail}</span>
      {withSource && gain.source_url ? (
        <>
          {" "}
          <a href={gain.source_url} target="_blank" rel="noreferrer">
            Kilde
          </a>
        </>
      ) : null}
    </span>
  );
}
