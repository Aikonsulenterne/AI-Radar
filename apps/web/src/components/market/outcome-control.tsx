"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ApiClientError, setMarketItemOutcome, type MarketCase } from "../../app/lib/api";

type Outcome = "positiv" | "negativ" | "blandet" | "";

/** Admin: ret casens resultat, fx når AI'en har læst en fejl som en succes.
 * En case, der ikke virkede, tæller aldrig som bevis. */
export function OutcomeControl({ item }: { item: MarketCase }) {
  const router = useRouter();
  const [value, setValue] = useState<Outcome>(item.outcome ?? "");
  const [message, setMessage] = useState<string | null>(null);

  async function choose(next: Outcome) {
    setValue(next);
    setMessage(null);
    try {
      await Promise.all(item.item_ids.map((id) => setMarketItemOutcome(id, next)));
      router.refresh();
    } catch (err) {
      setMessage(err instanceof ApiClientError ? err.message : "Kunne ikke gemme.");
    }
  }

  return (
    <label className="outcome-control no-print">
      <span>Admin · resultat</span>
      <select value={value} onChange={(e) => choose(e.target.value as Outcome)}>
        <option value="">Ikke oplyst</option>
        <option value="positiv">Virkede</option>
        <option value="blandet">Blandet resultat</option>
        <option value="negativ">Virkede ikke</option>
      </select>
      {message ? <span role="alert">{message}</span> : null}
    </label>
  );
}
