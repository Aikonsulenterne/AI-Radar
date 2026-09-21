import type { Metadata } from "next";
import { AppShell } from "../components/layout/app-shell";
import { AuthInit } from "../components/auth/auth-init";
import "../lib/register-server-auth";
import "../styles/globals.css";

// Fonte: OKfamily (display) og Fellix (body) aktiveres med next/font/local,
// når de licenserede filer er staged i public/fonts/ (se README dér).
// Indtil da bruges de godkendte fallbacks fra tokens — buildet må ikke
// fejle på manglende fontfiler (UI Master §4).

export const metadata: Metadata = {
  title: "AI Radar",
  description:
    "Internt, evidensbaseret technology-intelligence-produkt for OK.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="da">
      <body>
        <AuthInit />
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
