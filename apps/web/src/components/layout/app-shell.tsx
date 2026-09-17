import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";

export function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <>
      <a className="skip-link" href="#main">
        Spring til indhold
      </a>
      <div className="app-shell">
        <Sidebar />
        <div className="main-column">
          <Topbar />
          <main id="main" className="page">
            {children}
          </main>
        </div>
      </div>
    </>
  );
}
