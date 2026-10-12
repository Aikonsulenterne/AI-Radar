"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  ApiClientError,
  saveDecisionBrief,
  type DecisionBrief,
  type DecisionFinding,
  type PeerCall,
} from "../../lib/api";

// Udkast, som Admin kan indsætte og rette. Tallene om OK's indbakke stammer
// fra den interne FocalScope-analyse og skal efterprøves, før de bruges.
const DRAFT: Partial<DecisionBrief> = {
  ask: "En 30-dages sprint: 50 % af min tid, adgang til kontaktstatistik (volumen pr. kanal og AHT) og FocalScope-data, samt IT's godkendelse af at køre radaren i OK's eget miljø. Efter 30 dage beslutter vi, om vi går videre med en 60-dages pilot på 50–100.000 kr. til licenser og leverandør.",
  kill_criterion:
    "Kan jeg ikke efter 30 dage vise dokumenterede sparede timer eller en pilot, vi vil godkende, stopper vi. Så har vi brugt 30 dage af min tid og intet andet.",
  data_promise:
    "Ingen kundedata forlader OK. Radaren læser kun offentlige kilder; interne data analyseres kun i OK's eget miljø.",
  scenario_low_pct: 5,
  scenario_high_pct: 10,
  internal_findings: [
    {
      title: "Støj fra egne udsendelser (bounces)",
      figure: "86 i juni → 359 i august",
      description:
        "Tickets fra returnerede e-mails fra egne udsendelser. Skal verificeres.",
    },
    {
      title: "Automatiske kvitteringer i indbakken",
      figure: "1.055, heraf 37 nye tickets",
      description: "Kan filtreres fra uden AI-leverandør. Skal verificeres.",
    },
    {
      title: "Svar til no-reply-adressen",
      figure: "192 svar, 54 sager lukket uden svar",
      description:
        "Kunder svarer på no-reply@ok.dk; svaret når ikke frem. Skal verificeres.",
    },
  ],
  peer_calls: [
    { organization: "Andel Energi", status: "ikke booket", notes: null },
    { organization: "Norlys", status: "ikke booket", notes: null },
  ],
};

function toNumber(value: string): number | null {
  const cleaned = value.replace(/\./g, "").replace(",", ".").trim();
  if (cleaned === "") return null;
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
}

function NumberField({
  id,
  label,
  value,
  onChange,
  hint,
}: {
  id: string;
  label: string;
  value: number | null;
  onChange: (value: number | null) => void;
  hint?: string;
}) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        inputMode="decimal"
        defaultValue={value ?? ""}
        onChange={(event) => onChange(toNumber(event.target.value))}
        placeholder={hint}
      />
    </div>
  );
}

export function BriefForm({ initial }: { initial: DecisionBrief }) {
  const router = useRouter();
  const [brief, setBrief] = useState<DecisionBrief>(initial);
  const [formKey, setFormKey] = useState(0);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function set<K extends keyof DecisionBrief>(key: K, value: DecisionBrief[K]) {
    setBrief((current) => ({ ...current, [key]: value }));
  }

  function setText(key: keyof DecisionBrief, value: string) {
    setBrief((current) => ({
      ...current,
      [key]: value.trim() === "" ? null : value,
    }));
  }

  function insertDraft() {
    setBrief((current) => ({
      ...current,
      ask: current.ask ?? DRAFT.ask ?? null,
      kill_criterion: current.kill_criterion ?? DRAFT.kill_criterion ?? null,
      data_promise: current.data_promise ?? DRAFT.data_promise ?? null,
      scenario_low_pct:
        current.scenario_low_pct ?? DRAFT.scenario_low_pct ?? null,
      scenario_high_pct:
        current.scenario_high_pct ?? DRAFT.scenario_high_pct ?? null,
      internal_findings:
        current.internal_findings.length > 0
          ? current.internal_findings
          : (DRAFT.internal_findings ?? []),
      peer_calls:
        current.peer_calls.length > 0
          ? current.peer_calls
          : (DRAFT.peer_calls ?? []),
    }));
    setFormKey((k) => k + 1);
    setMessage("Forslaget er indsat — ret det til og gem.");
  }

  async function save() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await saveDecisionBrief(brief);
      setMessage("Gemt. Beslutningsoplægget er opdateret.");
      router.refresh();
    } catch (err) {
      setError(
        err instanceof ApiClientError
          ? err.message
          : "Oplægget kunne ikke gemmes.",
      );
    } finally {
      setBusy(false);
    }
  }

  function updateFinding(index: number, patch: Partial<DecisionFinding>) {
    set(
      "internal_findings",
      brief.internal_findings.map((f, i) =>
        i === index ? { ...f, ...patch } : f,
      ),
    );
  }

  function updatePeer(index: number, patch: Partial<PeerCall>) {
    set(
      "peer_calls",
      brief.peer_calls.map((p, i) => (i === index ? { ...p, ...patch } : p)),
    );
  }

  return (
    <form
      key={formKey}
      onSubmit={(event) => {
        event.preventDefault();
        void save();
      }}
    >
      <p>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={insertDraft}
        >
          Indsæt mit forslag
        </button>{" "}
        <span className="cell-sub">Udfylder kun tomme felter.</span>
      </p>

      <h2 className="section-title">Udgangspunkt</h2>
      <div className="field-row">
        <div className="field">
          <label htmlFor="system">Kontaktcentersystem</label>
          <input
            id="system"
            defaultValue={brief.contact_center_system ?? ""}
            onChange={(e) => setText("contact_center_system", e.target.value)}
            placeholder="fx Puzzel"
          />
        </div>
        <div className="field">
          <label htmlFor="renewal">Kontrakt udløber</label>
          <input
            id="renewal"
            defaultValue={brief.contract_renewal ?? ""}
            onChange={(e) => setText("contract_renewal", e.target.value)}
            placeholder="fx juni 2027"
          />
        </div>
        <div className="field">
          <label htmlFor="budget">Budgetfrist</label>
          <input
            id="budget"
            defaultValue={brief.budget_deadline ?? ""}
            onChange={(e) => setText("budget_deadline", e.target.value)}
            placeholder="fx 15. november 2026"
          />
        </div>
      </div>
      <div className="field-row">
        <NumberField
          id="fte"
          label="Årsværk"
          value={brief.fte}
          onChange={(v) => set("fte", v)}
        />
        <NumberField
          id="cost"
          label="Pris pr. årsværk (kr.)"
          value={brief.cost_per_fte}
          onChange={(v) => set("cost_per_fte", v)}
          hint="fx 450.000"
        />
        <NumberField
          id="aht"
          label="Gns. behandlingstid (min)"
          value={brief.aht_minutes}
          onChange={(v) => set("aht_minutes", v)}
        />
      </div>
      <div className="field-row">
        <NumberField
          id="phone"
          label="Opkald pr. år"
          value={brief.contacts_per_year.phone}
          onChange={(v) =>
            set("contacts_per_year", { ...brief.contacts_per_year, phone: v })
          }
        />
        <NumberField
          id="mail"
          label="Mails pr. år"
          value={brief.contacts_per_year.mail}
          onChange={(v) =>
            set("contacts_per_year", { ...brief.contacts_per_year, mail: v })
          }
        />
        <NumberField
          id="chat"
          label="Chats pr. år"
          value={brief.contacts_per_year.chat}
          onChange={(v) =>
            set("contacts_per_year", { ...brief.contacts_per_year, chat: v })
          }
        />
      </div>
      <div className="field-row">
        <NumberField
          id="low"
          label="Scenarie lav (% af arbejdet)"
          value={brief.scenario_low_pct}
          onChange={(v) => set("scenario_low_pct", v)}
        />
        <NumberField
          id="high"
          label="Scenarie høj (% af arbejdet)"
          value={brief.scenario_high_pct}
          onChange={(v) => set("scenario_high_pct", v)}
        />
      </div>

      <h2 className="section-title">Interne fund</h2>
      {brief.internal_findings.map((finding, index) => (
        <div className="field-row" key={index}>
          <div className="field">
            <label htmlFor={`f-title-${index}`}>Fund</label>
            <input
              id={`f-title-${index}`}
              defaultValue={finding.title}
              onChange={(e) => updateFinding(index, { title: e.target.value })}
            />
          </div>
          <div className="field">
            <label htmlFor={`f-figure-${index}`}>Tal</label>
            <input
              id={`f-figure-${index}`}
              defaultValue={finding.figure ?? ""}
              onChange={(e) =>
                updateFinding(index, { figure: e.target.value || null })
              }
            />
          </div>
          <div className="field">
            <label htmlFor={`f-desc-${index}`}>Forklaring</label>
            <input
              id={`f-desc-${index}`}
              defaultValue={finding.description ?? ""}
              onChange={(e) =>
                updateFinding(index, { description: e.target.value || null })
              }
            />
          </div>
          <div className="field">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => {
                set(
                  "internal_findings",
                  brief.internal_findings.filter((_, i) => i !== index),
                );
                // Felterne er ukontrollerede: tegn formularen igen efter fjernelse.
                setFormKey((k) => k + 1);
              }}
            >
              Fjern
            </button>
          </div>
        </div>
      ))}
      <p>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() =>
            set("internal_findings", [
              ...brief.internal_findings,
              { title: "Nyt fund", figure: null, description: null },
            ])
          }
        >
          Tilføj fund
        </button>
      </p>

      <h2 className="section-title">Ønsket</h2>
      {(
        [
          ["ask", "Det beder jeg om"],
          ["kill_criterion", "Stopkriterium"],
          ["data_promise", "Løfte om data"],
        ] as const
      ).map(([key, label]) => (
        <div className="field" key={key}>
          <label htmlFor={key}>{label}</label>
          <textarea
            id={key}
            rows={3}
            defaultValue={brief[key] ?? ""}
            onChange={(e) => setText(key, e.target.value)}
          />
        </div>
      ))}

      <h2 className="section-title">Samtaler med branchekolleger</h2>
      {brief.peer_calls.map((peer, index) => (
        <div className="field-row" key={index}>
          <div className="field">
            <label htmlFor={`p-org-${index}`}>Organisation</label>
            <input
              id={`p-org-${index}`}
              defaultValue={peer.organization}
              onChange={(e) =>
                updatePeer(index, { organization: e.target.value })
              }
            />
          </div>
          <div className="field">
            <label htmlFor={`p-status-${index}`}>Status</label>
            <input
              id={`p-status-${index}`}
              defaultValue={peer.status ?? ""}
              onChange={(e) =>
                updatePeer(index, { status: e.target.value || null })
              }
              placeholder="ikke booket / booket / afholdt"
            />
          </div>
          <div className="field">
            <label htmlFor={`p-notes-${index}`}>Noter</label>
            <input
              id={`p-notes-${index}`}
              defaultValue={peer.notes ?? ""}
              onChange={(e) =>
                updatePeer(index, { notes: e.target.value || null })
              }
            />
          </div>
        </div>
      ))}
      <p>
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() =>
            set("peer_calls", [
              ...brief.peer_calls,
              {
                organization: "Ny organisation",
                status: "ikke booket",
                notes: null,
              },
            ])
          }
        >
          Tilføj samtale
        </button>
      </p>

      {error ? (
        <div className="alert-error" role="alert">
          {error}
        </div>
      ) : null}
      {message ? (
        <p className="cell-sub" role="status">
          {message}
        </p>
      ) : null}
      <button type="submit" className="btn" disabled={busy}>
        Gem
      </button>
    </form>
  );
}
