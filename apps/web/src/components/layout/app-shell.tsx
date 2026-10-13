import { TopNav } from "./top-nav";
import { getMe } from "../../app/lib/me";

function formatUpdated(value: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  const day = new Intl.DateTimeFormat("da-DK", {
    day: "numeric",
    month: "short",
    timeZone: "Europe/Copenhagen",
  }).format(date);
  const time = new Intl.DateTimeFormat("da-DK", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Copenhagen",
  }).format(date);
  return `${day} kl. ${time}`;
}

export async function AppShell({ children }: Readonly<{ children: React.ReactNode }>) {
  const me = await getMe();
  return (
    <>
      <a className="skip-link" href="#main">
        Spring til indhold
      </a>
      <TopNav
        isAdmin={me?.role === "admin"}
        lastUpdated={formatUpdated(me?.last_updated ?? null)}
      />
      <main id="main" className="page page-v2">
        {children}
      </main>
    </>
  );
}
