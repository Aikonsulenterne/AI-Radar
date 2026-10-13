"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type NavItem = { href: string; label: string };

// Den forenklede radar (2026-10-13): tre spørgsmål, tre sider. Kilder er
// konsulentens værktøj og vises kun for Admin.
export const primaryNav: NavItem[] = [
  { href: "/", label: "Til OK" },
  { href: "/teknologier", label: "Teknologier" },
  { href: "/cases", label: "Sådan gør andre" },
];

export const adminNav: NavItem[] = [{ href: "/admin/sources", label: "Kilder" }];

export function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Sidebar({ isAdmin }: { isAdmin: boolean }) {
  const pathname = usePathname();

  return (
    <nav className="sidebar" aria-label="Hovednavigation">
      <Link href="/" className="sidebar-brand">
        AI Radar
      </Link>
      <p className="sidebar-sub">Salg · Kundeservice · Support</p>
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
      {isAdmin ? (
        <>
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
        </>
      ) : null}
      <div className="sidebar-foot">OK a.m.b.a. · hvert fund har en kilde</div>
    </nav>
  );
}
