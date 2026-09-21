"use client";

import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";

// Browser-klient til Supabase Auth. Anon-nøglen er offentlig by design;
// authorization håndhæves server-side i API'et (Technical Master §13).
let client: SupabaseClient | null = null;

export function getSupabaseBrowserClient(): SupabaseClient | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anonKey) return null;
  if (client === null) {
    client = createBrowserClient(url, anonKey);
  }
  return client;
}
