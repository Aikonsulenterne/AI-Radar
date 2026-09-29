/**
 * Markerer indhold, som AI har godkendt og publiceret uden menneskelig
 * kontrol (AUTO_PUBLISH). Tekst frem for farve alene (UI Master §3).
 */
export function AiPublishedBadge({ label = "AI-publiceret" }: { label?: string }) {
  return (
    <span
      className="badge badge-ai"
      title="Godkendt og publiceret automatisk af AI — intet menneske har kontrolleret indholdet."
    >
      {label}
    </span>
  );
}
