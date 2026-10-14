"use client";

import { useId, useState } from "react";
import type { OkBriefRow } from "../../app/lib/api";
import { StatusBadge } from "./status-badge";

export function ProblemRow({ row }: { row: OkBriefRow }) {
  const [open, setOpen] = useState(false);
  const detailsId = useId();
  return (
    <div className="brief-row">
      <button
        type="button"
        className="brief-grid brief-row-button"
        aria-expanded={open}
        aria-controls={detailsId}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="brief-problem">{row.title}</span>
        <span className="brief-tech">
          <span>{row.technology?.label ?? "Ikke oplyst"}</span>
          {row.technology ? (
            <StatusBadge status={row.technology.status} label={row.technology.status_label} />
          ) : null}
        </span>
        <span className="brief-proof">
          <span className="brief-proof-text">
            {row.proof.company}: {row.proof.text}
          </span>
          <span className="brief-proof-kind">
            {row.proof.kind_label}
            {row.proof.region_label ? ` · ${row.proof.country ?? row.proof.region_label}` : ""}
          </span>
        </span>
        <span className="brief-next">{row.next_step || "Ikke oplyst"}</span>
        <span className="brief-chev no-print" aria-hidden="true">
          {open ? "−" : "+"}
        </span>
      </button>
      {open ? (
        <div id={detailsId} className="brief-details no-print">
          <div className="box-analysis">
            <div className="box-label">Hvorfor beviset ligner OK</div>
            <p>{row.because || "Ikke oplyst"}</p>
            {row.proof.source_url ? (
              <a href={row.proof.source_url} target="_blank" rel="noreferrer">
                Kilde: {row.proof.source_title} →
              </a>
            ) : null}
          </div>
          <div className="box-plain">
            <div className="box-label">Flere cases</div>
            {row.more.length === 0 ? (
              <p className="muted">Ingen flere endnu.</p>
            ) : (
              row.more.map((c) => (
                <p key={c.id}>
                  <strong>{c.company}</strong>
                  {c.country ? ` · ${c.country}` : ""} – {c.what}{" "}
                  {c.source_url ? (
                    <a href={c.source_url} target="_blank" rel="noreferrer">
                      Kilde
                    </a>
                  ) : null}
                </p>
              ))
            )}
          </div>
          {row.lookup ? (
            <div className="box-plain">
              <div className="box-label">Slå op internt</div>
              <p>{row.lookup}</p>
              <p className="muted small">
                {row.effect_pct !== null
                  ? `Casen oplyser ${Math.round(row.effect_pct * 100)} %. `
                  : "Casen oplyser ingen procent. "}
                Regn kronerne ud i regnearket på OK&rsquo;s egen pc – radaren ser ikke jeres tal.
              </p>
            </div>
          ) : null}
          <div className="box-plain">
            <div className="box-label">Hvem kan vi tale med</div>
            <p>
              <span className="muted">Leverandører:</span>{" "}
              {row.vendors.length > 0 ? row.vendors.join(", ") : "Ikke oplyst"}
            </p>
            <p>
              <span className="muted">Reference:</span> {row.reference}
            </p>
          </div>
        </div>
      ) : null}
    </div>
  );
}
