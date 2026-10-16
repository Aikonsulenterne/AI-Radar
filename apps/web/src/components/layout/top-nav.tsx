"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserMenu } from "../auth/user-menu";

type NavItem = { href: string; label: string; admin?: boolean };

// Designhandoff v2 §2: højst fire punkter, Til OK er forsiden.
const NAV: NavItem[] = [
  { href: "/teknologier", label: "Teknologier" },
  { href: "/cases", label: "Sådan gør andre" },
  { href: "/", label: "Til OK" },
  { href: "/admin/sources", label: "Kilder", admin: true },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function TopNav({
  isAdmin,
  lastUpdated,
}: {
  isAdmin: boolean;
  lastUpdated: string | null;
}) {
  const pathname = usePathname();
  return (
    <header className="topnav no-print">
      <div className="topnav-inner">
        <Link href="/" className="topnav-brand">
          <span className="topnav-title">AI Radar</span>
          <span className="topnav-eyebrow">Kundecenter</span>
        </Link>
        <nav aria-label="Hovedmenu" className="topnav-links">
          {NAV.filter((item) => !item.admin || isAdmin).map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="topnav-link"
              aria-current={isActive(pathname, item.href) ? "page" : undefined}
            >
              {item.label}
              {item.admin ? <span className="topnav-admin">Admin</span> : null}
            </Link>
          ))}
        </nav>
        <div className="topnav-meta">
          {lastUpdated ? <span className="topnav-updated">Opdateret {lastUpdated}</span> : null}
          <UserMenu />
        </div>
      </div>
    </header>
  );
}
