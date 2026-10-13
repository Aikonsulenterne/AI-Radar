import type { TechStatus } from "../../app/lib/api";

/** Klar nu / Værd at afprøve / Hold øje med — teksten bærer betydningen,
 * farven understøtter den. Status beregnes af serveren. */
export function StatusBadge({ status, label }: { status: TechStatus; label: string }) {
  return <span className={`status-badge status-${status}`}>{label}</span>;
}
