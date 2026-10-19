"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ApiClientError, addMarketLink } from "../../app/lib/api";

/** Admin: tilføj en case fra et offentligt link — LinkedIn-opslag,
 * konferenceoplæg eller en kundecase. Radaren læser det med det samme med
 * samme regler som alt andet: ordret citat, tal skal stå i kilden. */
export function AddLinkForm() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [vendor, setVendor] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!url.trim()) return;
    setBusy(true);
    setMessage(null);
    try {
      const result = await addMarketLink(url.trim(), vendor);
      setMessage(result.message);
      if (!result.already_known) setUrl("");
      router.refresh();
    } catch (err) {
      setMessage(err instanceof ApiClientError ? err.message : "Linket kunne ikke læses.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="add-link" onSubmit={submit}>
      <label htmlFor="add-link-url" className="add-link-label">
        Tilføj case fra link
      </label>
      <div className="add-link-row">
        <input
          id="add-link-url"
          type="url"
          required
          placeholder="https://… (opslag, oplæg eller kundecase)"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
        <label className="add-link-vendor">
          <input type="checkbox" checked={vendor} onChange={(e) => setVendor(e.target.checked)} />
          Leverandørens egen side
        </label>
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? "Læser …" : "Læs linket"}
        </button>
      </div>
      <p className="muted small">
        Kun offentlige links. Radaren gemmer kun det, den kan citere ordret.
      </p>
      {message ? (
        <p className="add-link-message" role="status">
          {message}
        </p>
      ) : null}
    </form>
  );
}
