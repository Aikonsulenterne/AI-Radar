"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ApiClientError,
  updateTechnology,
  type TechHorizon,
  type Technology,
} from "../../lib/api";

const HORIZONS: { value: TechHorizon; label: string }[] = [
  { value: "now", label: "NU — modent og anvendeligt i dag" },
  { value: "next", label: "NÆSTE — bør undersøges snart" },
  { value: "horizon", label: "HORIZON — 1–3 år, højere usikkerhed" },
];

export function CandidateActions({ technology }: { technology: Technology }) {
  const router = useRouter();
  const [name, setName] = useState(technology.name);
  const [horizon, setHorizon] = useState<TechHorizon>("next");
  const [definition, setDefinition] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save(input: Parameters<typeof updateTechnology>[1]) {
    setBusy(true);
    setError(null);
    try {
      await updateTechnology(technology.id, input);
      router.refresh();
    } catch (err) {
      setError(
        err instanceof ApiClientError
          ? err.message
          : "Ændringen kunne ikke gemmes.",
      );
    } finally {
      setBusy(false);
    }
  }

  const idPrefix = `tech-${technology.id}`;
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        void save({ name: name.trim(), horizon, definition: definition.trim() });
      }}
    >
      <div className="field-row">
        <div className="field">
          <label htmlFor={`${idPrefix}-name`}>Navn</label>
          <input
            id={`${idPrefix}-name`}
            value={name}
            onChange={(event) => setName(event.target.value)}
            required
            maxLength={120}
          />
        </div>
        <div className="field">
          <label htmlFor={`${idPrefix}-horizon`}>Horisont</label>
          <select
            id={`${idPrefix}-horizon`}
            value={horizon}
            onChange={(event) => setHorizon(event.target.value as TechHorizon)}
          >
            {HORIZONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="field">
        <label htmlFor={`${idPrefix}-definition`}>Definition</label>
        <textarea
          id={`${idPrefix}-definition`}
          value={definition}
          onChange={(event) => setDefinition(event.target.value)}
          required
          maxLength={1000}
          rows={2}
          placeholder="Hvad dækker capability'en over?"
        />
      </div>
      {error ? (
        <div className="alert-error" role="alert">
          {error}
        </div>
      ) : null}
      <button type="submit" className="btn" disabled={busy}>
        Optag på radaren
      </button>{" "}
      <button
        type="button"
        className="btn btn-secondary"
        disabled={busy}
        onClick={() => void save({ active: false })}
      >
        Afvis
      </button>
    </form>
  );
}
