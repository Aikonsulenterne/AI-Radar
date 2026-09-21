import { setTokenProvider } from "../app/lib/api";
import { getServerAccessToken } from "./supabase/server";

// Registrerer server-sidens token-provider i api-lagets modulinstans.
// cookies() er AsyncLocalStorage-baseret, så providerfunktionen læser den
// aktuelle requests session, selvom registreringen kun sker én gang.
setTokenProvider(getServerAccessToken);
