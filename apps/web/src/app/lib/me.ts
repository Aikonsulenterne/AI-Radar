import { cache } from "react";
import { getMe, type Me } from "./api";

/** Den indloggede brugers rolle, én gang pr. request (layout og side deler
 * svaret). null = ikke logget ind eller API'et svarer ikke. */
export const getRole = cache(async (): Promise<Me["role"] | null> => {
  try {
    return (await getMe()).role;
  } catch {
    return null;
  }
});
