"use client";

import { setTokenProvider } from "../../app/lib/api";
import { getSupabaseBrowserClient } from "../../lib/supabase/client";

// Registrerer browser-sidens token-provider i client-bundlets api-modul.
// Kører ved modul-load, før nogen client component kalder API'et.
setTokenProvider(async () => {
  const supabase = getSupabaseBrowserClient();
  if (!supabase) return null;
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
});

export function AuthInit() {
  return null;
}
