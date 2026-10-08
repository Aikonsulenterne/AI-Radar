import type { Technology } from "../../app/lib/api";

const HORIZON_LABELS: Record<NonNullable<Technology["horizon"]>, string> = {
  now: "NU",
  next: "NÆSTE",
  horizon: "HORIZON",
};

/** Horisont — eller "Ny i markedet" for en kandidat, der ikke er kurateret. */
export function HorizonBadge({
  technology,
}: {
  technology: Pick<Technology, "horizon" | "is_candidate">;
}) {
  if (technology.horizon === null) {
    return <span className="badge badge-candidate">Ny i markedet · ikke kurateret</span>;
  }
  return (
    <span className={`badge badge-horizon-${technology.horizon}`}>
      {HORIZON_LABELS[technology.horizon]}
    </span>
  );
}
