"use client";

import type { MarketTechnologyRef } from "../../app/lib/api";
import { FilterSelect } from "./filter-select";

export function TechnologySelect({
  options,
  current,
}: {
  options: MarketTechnologyRef[];
  current: string | undefined;
}) {
  return (
    <FilterSelect
      label="Teknologi"
      param="teknologi"
      allLabel="Alle teknologier"
      options={options.map((o) => ({ value: o.id, label: o.label }))}
      current={current}
    />
  );
}
