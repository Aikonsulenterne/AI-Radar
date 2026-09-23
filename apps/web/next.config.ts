import type { NextConfig } from "next";

// NEXT_PUBLIC_* bages ind i buildet. Mangler de på Vercel, deployes en side,
// der tror den kører lokalt (intet login, API på localhost). Fejl buildet i
// stedet, så fejlen ses i Vercel og den forrige deployment bliver stående.
if (process.env.VERCEL) {
  const missing = [
    "NEXT_PUBLIC_API_BASE_URL",
    "NEXT_PUBLIC_SUPABASE_URL",
    "NEXT_PUBLIC_SUPABASE_ANON_KEY",
  ].filter((key) => !process.env[key]);
  if (missing.length > 0) {
    throw new Error(
      `Mangler miljøvariabler i Vercel (${process.env.VERCEL_ENV ?? "ukendt miljø"}): ` +
        `${missing.join(", ")}. Sæt dem under Settings → Environment Variables og redeploy.`,
    );
  }
}

const nextConfig: NextConfig = {
  // Standalone output så frontenden også kan køre som container (portabilitetskrav).
  output: "standalone",
};

export default nextConfig;
