export function EmptyState({
  slice,
  children,
}: Readonly<{ slice: string; children: React.ReactNode }>) {
  return (
    <div className="empty-state">
      <p>
        <strong>Ingen data endnu.</strong>
      </p>
      <p>{children}</p>
      <p>Funktionaliteten bygges i {slice} (Technical Master §20).</p>
    </div>
  );
}
