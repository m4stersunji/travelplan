/**
 * Shared `x-api-key` check for write endpoints. Reads stay public.
 * If API_SECRET is unset, allow all (dev-friendly default).
 */
export function isAuthorized(headers: Headers, apiSecret: string | undefined): boolean {
  if (!apiSecret) return true;
  return headers.get("x-api-key") === apiSecret;
}
