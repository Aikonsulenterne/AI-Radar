"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type NavItem = { href: string; label: string };

const primaryNav: NavItem[] = [
  { href: "/", label: "Overblik" },
  { href: "/adoption", label: "AI-adoption" },
  { href: "/technologies", label: "Teknologiradar" },
  { href: "/opportunities", label: "Opportunities" },
  { href: "/sources", label: "Kilder og metode" },
  { href: "/briefing", label: "Briefing" },
];

const adminNav: NavItem[] = [
  { href: "/admin/review", label: "Review" },
  { href: "/admin/sources", label: "Source Registry" },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function SideNav() {
  const pathname = usePathname();

  return (
    <nav className="sidenav" aria-label="Hovednavigation">
      <div className="sidenav-brand">AI Radar</div>
      {primaryNav.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className="sidenav-link"
          aria-current={isActive(pathname, item.href) ? "page" : undefined}
        >
          {item.label}
        </Link>
      ))}
      <div className="sidenav-section">Administration</div>
      {adminNav.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className="sidenav-link"
          aria-current={isActive(pathname, item.href) ? "page" : undefined}
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
