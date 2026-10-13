"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { setMarketItemHidden } from "../../app/lib/api";

/** Konsulentens værktøj: skjul et forkert fund. Intet slettes, og
 * handlingen står i audit-loggen. */
export function HideButton({ itemIds, label = "Skjul" }: { itemIds: string[]; label?: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function hide() {
    if (!window.confirm("Skjul dette fund for alle? Det kan vises igen fra audit-loggen.")) return;
    setBusy(true);
    setError(null);
    try {
      for (const id of itemIds) await setMarketItemHidden(id, true);
      router.refresh();
    } catch {
      setError("Kunne ikke skjule. Prøv igen.");
      setBusy(false);
    }
  }

  return (
    <span className="no-print">
      <button type="button" className="btn-link hide-button" onClick={hide} disabled={busy}>
        {busy ? "Skjuler …" : label}
      </button>
      {error ? <span className="cell-sub">{error}</span> : null}
    </span>
  );
}
