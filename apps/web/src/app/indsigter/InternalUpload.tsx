"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ApiClientError,
  createSource,
  listSources,
  processDocument,
  uploadDocument,
  type Source,
} from "../lib/api";

const INTERNAL_SOURCE_NAME = "Interne data (OK)";

async function internalSource(): Promise<Source> {
  const sources = (await listSources()).items;
  const existing =
    sources.find(
      (s) => s.name === INTERNAL_SOURCE_NAME && s.access_class === "restricted",
    ) ??
    sources.find(
      (s) =>
        s.access_class === "restricted" &&
        s.retrieval_method === "manual_upload",
    );
  if (existing) return existing;
  return createSource({
    name: INTERNAL_SOURCE_NAME,
    source_type: "primary",
    retrieval_method: "manual_upload",
    access_class: "restricted",
    notes: "Interne, anonymiserede OK-data til Indsigter. Ingen kundedata.",
  });
}

/** Upload af en intern eksport. Kræver Admin og en bekræftelse af, at filen
 *  ikke indeholder kundedata — dokumentteksten sendes til AI-modellen. */
export function InternalUpload() {
  const router = useRouter();
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setBusy(true);
    setError(null);
    setMessage("Uploader …");
    try {
      const source = await internalSource();
      const upload = await uploadDocument(source.id, file);
      if (!upload.created) {
        setMessage("Filen er allerede uploadet (samme indhold).");
        return;
      }
      setMessage("Analyserer — det kan tage et minut …");
      const result = await processDocument(upload.document.id);
      setMessage(
        result.claims_created > 0
          ? `Færdig: ${result.claims_created} fund udtrukket. Analysen vises ovenfor.`
          : "Analysen fandt ingen målbare fund i filen.",
      );
      router.refresh();
    } catch (err) {
      setMessage(null);
      setError(
        err instanceof ApiClientError
          ? err.message
          : "Upload eller analyse fejlede. Prøv igen om lidt.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="signal-section" aria-label="Tilføj intern analyse">
      <h2 className="section-title">
        Tilføj intern analyse <span className="section-tag">Kræver Admin</span>
      </h2>
      <p>
        Upload en eksport eller analyse af OK&#8217;s egne data (tekst, CSV,
        Markdown eller PDF). Radaren udtrækker målbare fund med ordrette citater
        og laver en intern analyse, der aldrig vises som markedsviden.
      </p>
      <div className="alert-error" role="note">
        Filens tekst sendes til AI-modellen. Upload kun aggregerede eller
        anonymiserede tal — ingen kundenavne, adresser, telefonnumre,
        kundenumre, e-mailadresser eller samtaleindhold.
      </div>
      <p>
        <label>
          <input
            type="checkbox"
            checked={confirmed}
            onChange={(event) => setConfirmed(event.target.checked)}
          />{" "}
          Jeg bekræfter, at filen ikke indeholder kundedata eller andre
          personoplysninger.
        </label>
      </p>
      <input
        type="file"
        accept=".txt,.csv,.md,.pdf,.html"
        disabled={!confirmed || busy}
        onChange={(event) => void handleFile(event)}
        aria-label="Vælg fil med interne data"
      />
      {message ? (
        <p className="cell-sub" role="status">
          {message}
        </p>
      ) : null}
      {error ? (
        <div className="alert-error" role="alert">
          {error}
        </div>
      ) : null}
    </section>
  );
}
