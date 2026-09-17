import type { Metadata } from "next";
import { SideNav } from "./components/SideNav";
import "./globals.css";

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
        <a className="skip-link" href="#main">
          Spring til indhold
        </a>
        <div className="app-shell">
          <SideNav />
          <div className="main-column">
            <header className="topbar">
              <span className="topbar-title">AI Radar</span>
              <span className="topbar-meta">
                Internt beslutningsprodukt — evidens før AI
              </span>
            </header>
            <main id="main" className="page">
              {children}
            </main>
          </div>
        </div>
      </body>
    </html>
  );
}
