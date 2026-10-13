import { cache } from "react";
import { getMe as fetchMe, type Me } from "./api";

/** Den indloggede bruger én gang pr. request (layout og side deler svaret).
 * null = ikke logget ind eller API'et svarer ikke. */
export const getMe = cache(async (): Promise<Me | null> => {
  try {
    return await fetchMe();
  } catch {
    return null;
  }
});

export async function getRole(): Promise<Me["role"] | null> {
  return (await getMe())?.role ?? null;
}
