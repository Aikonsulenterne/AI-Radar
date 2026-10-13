import Link from "next/link";

export type Tab = { value: string | undefined; label: string };

export const AREA_TABS: Tab[] = [
  { value: undefined, label: "Alle" },
  { value: "salg", label: "Salg" },
  { value: "kundeservice", label: "Kundeservice" },
  { value: "support", label: "Support" },
];

/** Faner som almindelige links: filteret står i URL'en, så en visning kan
 * deles og genindlæses. Øvrige filtre bevares. */
export function FilterTabs({
  label,
  param,
  tabs,
  current,
  basePath,
  params,
}: {
  label: string;
  param: string;
  tabs: Tab[];
  current: string | undefined;
  basePath: string;
  params: Record<string, string | undefined>;
}) {
  return (
    <nav className="filter-tabs" aria-label={label}>
      {tabs.map((tab) => {
        const search = new URLSearchParams();
        for (const [key, value] of Object.entries({ ...params, [param]: tab.value })) {
          if (value) search.set(key, value);
        }
        const href = search.toString() ? `${basePath}?${search}` : basePath;
        const active = (current ?? undefined) === tab.value;
        return (
          <Link
            key={tab.label}
            href={href}
            className="filter-tab"
            aria-current={active ? "page" : undefined}
          >
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}
