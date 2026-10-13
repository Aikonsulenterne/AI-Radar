import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";
import { getRole } from "../../app/lib/me";

export async function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const role = await getRole();
  return (
    <>
      <a className="skip-link" href="#main">
        Spring til indhold
      </a>
      <div className="app-shell">
        <Sidebar isAdmin={role === "admin"} />
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
