"use client";

import { usePathname } from "next/navigation";
import { UserMenu } from "../auth/user-menu";
import { adminNav, isActive, primaryNav } from "./sidebar";

function pageTitle(pathname: string): string {
  const match = [...adminNav, ...primaryNav].find((item) =>
    isActive(pathname, item.href),
  );
  if (pathname.startsWith("/signals/")) return "Signal";
  if (pathname.startsWith("/adoption/cases/")) return "Adoption case";
  if (pathname.startsWith("/adoption/companies/")) return "Virksomhed";
  if (pathname.startsWith("/technologies/")) return "Teknologi";
  if (pathname.startsWith("/opportunities/")) return "Opportunity";
  if (pathname === "/login") return "Log ind";
  return match?.label ?? "AI Radar";
}

export function Topbar() {
  const pathname = usePathname();

  return (
    <header className="topbar">
      <span className="topbar-title">{pageTitle(pathname)}</span>
      <UserMenu />
    </header>
  );
}
