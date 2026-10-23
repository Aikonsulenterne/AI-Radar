"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

/** Et filter som rullemenu, der skriver sit valg i URL'en. */
export function FilterSelect({
  label,
  param,
  allLabel,
  options,
  current,
}: {
  label: string;
  param: string;
  allLabel: string;
  options: { value: string; label: string }[];
  current: string | undefined;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  function choose(value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set(param, value);
    else params.delete(param);
    const text = params.toString();
    router.push(text ? `${pathname}?${text}` : pathname);
  }

  return (
    <label className="filter-select">
      <span>{label}</span>
      <select value={current ?? ""} onChange={(event) => choose(event.target.value)}>
        <option value="">{allLabel}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
