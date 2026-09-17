"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ApiClientError,
  createSource,
  type AccessClass,
  type Frequency,
  type RetrievalMethod,
  type SourceType,
} from "../../lib/api";

const SOURCE_TYPES: { value: SourceType; label: string }[] = [
  { value: "primary", label: "Primær" },
  { value: "independent_analysis", label: "Uafhængig analyse" },
  { value: "vendor_case", label: "Leverandørcase" },
  { value: "vendor_claim", label: "Leverandørudsagn" },
  { value: "media", label: "Medie" },
  { value: "research", label: "Forskning" },
  { value: "early_signal", label: "Tidligt signal" },
];

const RETRIEVAL_METHODS: { value: RetrievalMethod; label: string }[] = [
  { value: "manual_upload", label: "Manuel upload" },
  { value: "web_fetch", label: "Web fetch" },
  { value: "rss", label: "RSS (senere)" },
];

const ACCESS_CLASSES: { value: AccessClass; label: string }[] = [
  { value: "public", label: "Public" },
  { value: "licensed", label: "Licensed" },
  { value: "restricted", label: "Restricted" },
];

const FREQUENCIES: { value: Frequency; label: string }[] = [
  { value: "manual", label: "Manuel" },
  { value: "daily", label: "Dagligt" },
  { value: "weekly", label: "Ugentligt" },
  { value: "monthly", label: "Månedligt" },
];

export function CreateSourceForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [sourceType, setSourceType] = useState<SourceType>("media");
  const [retrievalMethod, setRetrievalMethod] =
    useState<RetrievalMethod>("manual_upload");
  const [accessClass, setAccessClass] = useState<AccessClass>("public");
  const [frequency, setFrequency] = useState<Frequency>("manual");
  const [endpointUrl, setEndpointUrl] = useState("");
  const [countryCode, setCountryCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const needsEndpoint =
    retrievalMethod === "web_fetch" || retrievalMethod === "rss";

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await createSource({
        name,
        source_type: sourceType,
        retrieval_method: retrievalMethod,
        access_class: accessClass,
        frequency,
        endpoint_url: needsEndpoint ? endpointUrl : null,
        country_code: countryCode ? countryCode.toUpperCase() : null,
      });
      setName("");
      setEndpointUrl("");
      setCountryCode("");
      router.refresh();
    } catch (err) {
      setError(
        err instanceof ApiClientError
          ? err.message
          : "Kilden kunne ikke oprettes. Kører API'et?",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card form-grid" onSubmit={handleSubmit}>
      <h2 className="form-title">Opret kilde</h2>
      <div className="field">
        <label htmlFor="source-name">Navn</label>
        <input
          id="source-name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          maxLength={200}
        />
      </div>
      <div className="field-row">
        <div className="field">
          <label htmlFor="source-type">Kildetype</label>
          <select
            id="source-type"
            value={sourceType}
            onChange={(e) => setSourceType(e.target.value as SourceType)}
          >
            {SOURCE_TYPES.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="retrieval-method">Hentemetode</label>
          <select
            id="retrieval-method"
            value={retrievalMethod}
            onChange={(e) =>
              setRetrievalMethod(e.target.value as RetrievalMethod)
            }
          >
            {RETRIEVAL_METHODS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="access-class">Access class</label>
          <select
            id="access-class"
            value={accessClass}
            onChange={(e) => setAccessClass(e.target.value as AccessClass)}
          >
            {ACCESS_CLASSES.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="frequency">Frekvens</label>
          <select
            id="frequency"
            value={frequency}
            onChange={(e) => setFrequency(e.target.value as Frequency)}
          >
            {FREQUENCIES.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </div>
      </div>
      {needsEndpoint ? (
        <div className="field">
          <label htmlFor="endpoint-url">Endpoint URL</label>
          <input
            id="endpoint-url"
            type="url"
            value={endpointUrl}
            onChange={(e) => setEndpointUrl(e.target.value)}
            required
            placeholder="https://…"
          />
        </div>
      ) : null}
      <div className="field field-narrow">
        <label htmlFor="country-code">Landekode (valgfri)</label>
        <input
          id="country-code"
          value={countryCode}
          onChange={(e) => setCountryCode(e.target.value)}
          maxLength={2}
          placeholder="DK"
          pattern="[A-Za-z]{2}"
        />
      </div>
      {error ? (
        <p className="alert-error" role="alert">
          {error}
        </p>
      ) : null}
      <div>
        <button type="submit" className="btn" disabled={busy}>
          {busy ? "Opretter…" : "Opret kilde"}
        </button>
      </div>
    </form>
  );
}
