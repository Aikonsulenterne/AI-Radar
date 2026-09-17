import type { DocumentationLevel, SignalStatus } from "./api";

// Dokumentationsstyrke (Product Master §11) — vises altid med tekst,
// aldrig kun farve.
export const DOCUMENTATION_LABELS: Record<DocumentationLevel, string> = {
  strong: "Stærk dokumentation",
  limited: "Begrænset dokumentation",
  early: "Tidligt signal",
  conflicting: "Modstridende",
};

export const SIGNAL_STATUS_LABELS: Record<SignalStatus, string> = {
  draft: "Kladde",
  published: "Publiceret",
  archived: "Arkiveret",
};

export function formatDateTime(value: string | null): string {
  if (!value) return "–";
  return new Intl.DateTimeFormat("da-DK", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "Europe/Copenhagen",
  }).format(new Date(value));
}
