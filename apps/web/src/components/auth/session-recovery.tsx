"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getSupabaseBrowserClient } from "../../lib/supabase/client";

/**
 * Vises, når serveren fik 401 fra API'et. Ofte er browserens session stadig
 * gyldig — adgangsbilletten var blot udløbet i det øjeblik, siden blev
 * renderet. Så fornyes sessionen her, og siden hentes igen, i stedet for at
 * brugeren sendes til login. Kun hvis der ingen session er, vises Log ind.
 */
const ATTEMPT_KEY = "ai-radar-session-recovery";
const ATTEMPT_WINDOW_MS = 30_000;

function recentlyAttempted(): boolean {
  try {
    const last = Number(window.sessionStorage.getItem(ATTEMPT_KEY) ?? 0);
    return Date.now() - last < ATTEMPT_WINDOW_MS;
  } catch {
    return false;
  }
}

function markAttempt(): void {
  try {
    window.sessionStorage.setItem(ATTEMPT_KEY, String(Date.now()));
  } catch {
    // Uden sessionStorage forsøges der blot hver gang.
  }
}

export function SessionRecovery() {
  const router = useRouter();
  const [state, setState] = useState<"checking" | "signed_out">("checking");

  useEffect(() => {
    const supabase = getSupabaseBrowserClient();
    if (!supabase || recentlyAttempted()) {
      // Højst ét forsøg pr. halve minut, så en vedvarende 401 aldrig giver
      // en løkke af genindlæsninger.
      setState("signed_out");
      return;
    }
    markAttempt();
    let cancelled = false;
    supabase.auth.refreshSession().then(({ data }) => {
      if (cancelled) return;
      if (data.session) {
        router.refresh();
      } else {
        setState("signed_out");
      }
    });
    return () => {
      cancelled = true;
    };
  }, [router]);

  if (state === "checking") {
    return (
      <p className="cell-sub" role="status">
        Fornyer din session…
      </p>
    );
  }
  return (
    <div className="alert-error" role="alert">
      Du er ikke logget ind. <Link href="/login">Log ind</Link> for at se
      indholdet.
    </div>
  );
}
