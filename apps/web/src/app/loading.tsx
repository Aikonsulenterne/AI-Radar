// Vises straks ved navigation, mens siden hentes fra API'et. Uden den
// står den gamle side stille, til den nye er færdig.
export default function Loading() {
  return (
    <div className="page-loading" role="status" aria-live="polite">
      <span className="visually-hidden">Henter siden …</span>
      <div className="skeleton skeleton-title" />
      <div className="skeleton skeleton-line" />
      <div className="skeleton skeleton-card" />
      <div className="skeleton skeleton-card" />
    </div>
  );
}
