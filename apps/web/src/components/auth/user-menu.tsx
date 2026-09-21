"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getSupabaseBrowserClient } from "../../lib/supabase/client";

export function UserMenu() {
  const router = useRouter();
  const supabase = getSupabaseBrowserClient();
  const [email, setEmail] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!supabase) {
      setReady(true);
      return;
    }
    supabase.auth.getUser().then(({ data }) => {
      setEmail(data.user?.email ?? null);
      setReady(true);
    });
    const { data: listener } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setEmail(session?.user?.email ?? null);
      },
    );
    return () => listener.subscription.unsubscribe();
  }, [supabase]);

  if (!supabase) {
    return <span className="topbar-meta">Lokal udvikling — uden login</span>;
  }
  if (!ready) return null;

  if (email === null) {
    return (
      <Link href="/login" className="btn btn-secondary">
        Log ind
      </Link>
    );
  }

  async function handleSignOut() {
    if (!supabase) return;
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  return (
    <span className="user-menu">
      <span className="topbar-meta">{email}</span>
      <button type="button" className="btn btn-secondary" onClick={handleSignOut}>
        Log ud
      </button>
    </span>
  );
}
