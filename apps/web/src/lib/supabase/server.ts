import { cookies } from "next/headers";
import { createServerClient } from "@supabase/ssr";

// Server-side Supabase-klient bundet til requestens cookies (Next 15:
// cookies() er async). Bruges kun fra server components.
export async function getServerAccessToken(): Promise<string | null> {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anonKey) return null;

  const cookieStore = await cookies();
  const supabase = createServerClient(url, anonKey, {
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll() {
        // Server components må ikke skrive cookies; refresh sker i middleware.
      },
    },
  });
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}
