import Link from "next/link";
import type { Claim } from "../../app/lib/api";
import {
  PREDICATE_LABELS,
  SOURCE_TYPE_LABELS,
  STAGE_LABELS,
  isVendorSource,
  predicateLabel,
} from "../../app/lib/labels";

// Korte værdier vises som mærker; effekter, barrierer og formål er
// sætninger og vises som punkter.
const SHORT_VALUE_PREDICATES = new Set([
  "OFFERS_CAPABILITY",
  "OFFERS_IN_MARKET",
  "SUPPORTS_LANGUAGE",
  "USES_CAPABILITY",
  "USES_TECHNOLOGY",
  "USES_VENDOR",
  "ADOPTION_STAGE",
]);
// Længere værdier er sætninger, også under et "kort" predicate.
const MAX_CHIP_CHARS = 40;
const PREDICATE_ORDER = Object.keys(PREDICATE_LABELS);
const APPROVED = new Set(["approved", "approved_with_edits"]);

interface FactValue {
  key: string;
  text: string;
  href: string | null;
  unapproved: boolean;
}

interface FactRow {
  predicate: string;
  values: FactValue[];
}

interface Quote {
  text: string;
  sourceType: string | null;
}

interface Subject {
  name: string;
  href: string | null;
}

interface FactGroup {
  key: string;
  subjects: Subject[];
  claimCount: number;
  rows: FactRow[];
  quotes: Quote[];
}

function entityHref(
  type: Claim["subject_entity_type"] | null,
  id: string | null,
): string | null {
  if (!id) return null;
  if (type === "technology") return `/technologies/${id}`;
  if (type === "company") return `/adoption/companies/${id}`;
  return null;
}

function valueText(claim: Claim): string {
  const raw = claim.object_name ?? claim.object_text ?? "Ikke dokumenteret";
  return claim.predicate === "ADOPTION_STAGE"
    ? (STAGE_LABELS[raw] ?? raw)
    : raw;
}

/** Claims samlet pr. subjekt og predicate; hvert citat vises én gang. */
export function groupFacts(claims: Claim[]): FactGroup[] {
  const groups = new Map<string, FactGroup>();
  for (const claim of claims) {
    const key = `${claim.subject_entity_type}:${claim.subject_entity_id}`;
    let group = groups.get(key);
    if (!group) {
      group = {
        key,
        subjects: [
          {
            name: claim.subject_name ?? "(ukendt)",
            href: entityHref(
              claim.subject_entity_type,
              claim.subject_entity_id,
            ),
          },
        ],
        claimCount: 0,
        rows: [],
        quotes: [],
      };
      groups.set(key, group);
    }
    group.claimCount += 1;

    let row = group.rows.find((r) => r.predicate === claim.predicate);
    if (!row) {
      row = { predicate: claim.predicate, values: [] };
      group.rows.push(row);
    }
    const text = valueText(claim);
    if (!row.values.some((v) => v.text.toLowerCase() === text.toLowerCase())) {
      row.values.push({
        key: claim.id,
        text,
        href: entityHref(claim.object_entity_type, claim.object_entity_id),
        unapproved: !APPROVED.has(claim.review_status),
      });
    }

    for (const evidence of claim.evidence) {
      const quote = evidence.supporting_excerpt.split(/\s+/).join(" ").trim();
      if (quote && !group.quotes.some((q) => q.text === quote)) {
        group.quotes.push({
          text: quote,
          sourceType: evidence.source_type_snapshot,
        });
      }
    }
  }

  const order = (predicate: string) => {
    const index = PREDICATE_ORDER.indexOf(predicate);
    return index === -1 ? PREDICATE_ORDER.length : index;
  };
  // Virksomheder med præcis samme fakta og citater (fx "Airbnb og Regal
  // Theaters har eksperimenteret med …") vises som én gruppe.
  const merged = new Map<string, FactGroup>();
  for (const group of groups.values()) {
    group.rows.sort((a, b) => order(a.predicate) - order(b.predicate));
    const signature = JSON.stringify([
      group.rows.map((r) => [r.predicate, r.values.map((v) => v.text)]),
      group.quotes.map((q) => q.text),
    ]);
    const existing = merged.get(signature);
    if (existing) {
      existing.subjects.push(...group.subjects);
      existing.claimCount += group.claimCount;
    } else {
      merged.set(signature, group);
    }
  }
  // Stabil sortering: flest fakta først, ellers kildens rækkefølge.
  return [...merged.values()].sort((a, b) => b.claimCount - a.claimCount);
}

/** Citatet i anførselstegn, medmindre det selv starter med et. */
function quoted(text: string): string {
  return /^["“”„«]/.test(text) ? text : `\u201c${text}\u201d`;
}

function FactValueView({ value }: { value: FactValue }) {
  const label = value.href ? (
    <Link href={value.href}>{value.text}</Link>
  ) : (
    value.text
  );
  return (
    <>
      {label}
      {value.unapproved ? (
        <span className="fact-unapproved"> (ikke godkendt)</span>
      ) : null}
    </>
  );
}

function FactRowValues({ row }: { row: FactRow }) {
  const asChip = (value: FactValue) =>
    SHORT_VALUE_PREDICATES.has(row.predicate) &&
    value.text.length <= MAX_CHIP_CHARS;
  const chips = row.values.filter(asChip);
  const sentences = row.values.filter((value) => !asChip(value));
  return (
    <>
      {chips.length > 0 ? (
        <ul className="fact-chips">
          {chips.map((value) => (
            <li className="fact-chip" key={value.key}>
              <FactValueView value={value} />
            </li>
          ))}
        </ul>
      ) : null}
      {sentences.length > 0 ? (
        <ul className="fact-sentences">
          {sentences.map((value) => (
            <li key={value.key}>
              <FactValueView value={value} />
            </li>
          ))}
        </ul>
      ) : null}
    </>
  );
}

export function FactGroups({
  claims,
  showSubject = true,
  empty = "Ingen claims tilknyttet.",
}: {
  claims: Claim[];
  /** Fra på sider, hvor alle claims har samme subjekt (virksomhed, case). */
  showSubject?: boolean;
  empty?: string;
}) {
  if (claims.length === 0) {
    return <p className="cell-sub">{empty}</p>;
  }
  const groups = groupFacts(claims);
  return (
    <div className="fact-groups">
      {groups.map((group) => (
        <article className="fact-group" key={group.key}>
          {showSubject ? (
            <h3 className="fact-subject">
              {group.subjects.map((subject, index) => (
                <span key={`${subject.name}-${index}`}>
                  {index > 0
                    ? index === group.subjects.length - 1
                      ? " og "
                      : ", "
                    : null}
                  {subject.href ? (
                    <Link href={subject.href}>{subject.name}</Link>
                  ) : (
                    subject.name
                  )}
                </span>
              ))}
            </h3>
          ) : null}
          <dl className="fact-rows">
            {group.rows.map((row) => (
              <div className="fact-row" key={row.predicate}>
                <dt>{predicateLabel(row.predicate)}</dt>
                <dd>
                  <FactRowValues row={row} />
                </dd>
              </div>
            ))}
          </dl>
          {group.quotes.length > 0 ? (
            <details className="fact-quotes">
              <summary>
                {group.quotes.length === 1
                  ? "Se kildecitatet"
                  : `Se ${group.quotes.length} kildecitater`}
              </summary>
              {group.quotes.map((quote) => (
                <blockquote className="evidence-quote" key={quote.text}>
                  {quoted(quote.text)}
                  {quote.sourceType ? (
                    <footer className="cell-sub">
                      {SOURCE_TYPE_LABELS[quote.sourceType] ?? quote.sourceType}
                      {isVendorSource(quote.sourceType)
                        ? " · leverandørens egne ord"
                        : ""}
                    </footer>
                  ) : null}
                </blockquote>
              ))}
            </details>
          ) : null}
        </article>
      ))}
    </div>
  );
}
