"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { MarketTechnologyRef } from "../../app/lib/api";

export function TechnologySelect({
  options,
  current,
}: {
  options: MarketTechnologyRef[];
  current: string | undefined;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  function choose(value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set("teknologi", value);
    else params.delete("teknologi");
    const text = params.toString();
    router.push(text ? `${pathname}?${text}` : pathname);
  }

  return (
    <label className="filter-select">
      <span>Teknologi</span>
      <select value={current ?? ""} onChange={(event) => choose(event.target.value)}>
        <option value="">Alle teknologier</option>
        {options.map((option) => (
          <option key={option.id} value={option.id}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
