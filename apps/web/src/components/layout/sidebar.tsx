"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type NavItem = { href: string; label: string };

// Primær navigation jf. UI Master §6.
export const primaryNav: NavItem[] = [
  { href: "/", label: "Overblik" },
  { href: "/adoption", label: "AI-adoption" },
  { href: "/technologies", label: "Teknologiradar" },
  { href: "/opportunities", label: "Opportunities" },
  { href: "/briefing", label: "Briefing" },
  { href: "/sources", label: "Kilder & metode" },
];

export const adminNav: NavItem[] = [
  { href: "/admin/review", label: "Review" },
  { href: "/admin/signals", label: "Signaler" },
  { href: "/admin/cases", label: "Cases" },
  { href: "/admin/sources", label: "Sources" },
];

export function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Sidebar() {
  const pathname = usePathname();

  return (
    <nav className="sidebar" aria-label="Hovednavigation">
      <Link href="/" className="sidebar-brand">
        AI Radar
      </Link>
      <p className="sidebar-sub">Technology Intelligence</p>
      {primaryNav.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className="sidebar-link"
          aria-current={isActive(pathname, item.href) ? "page" : undefined}
        >
          {item.label}
        </Link>
      ))}
      <div className="sidebar-section">Administration</div>
      {adminNav.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className="sidebar-link"
          aria-current={isActive(pathname, item.href) ? "page" : undefined}
        >
          {item.label}
        </Link>
      ))}
      <div className="sidebar-foot">Internt beslutningsprodukt · evidens før AI</div>
    </nav>
  );
}
