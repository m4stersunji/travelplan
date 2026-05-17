/**
 * Shared `x-api-key` check for write endpoints. Reads stay public.
 *
 * Fail closed: if API_SECRET is unset the worker has no way to authenticate
 * anyone, so we reject every write rather than silently allowing the world
 * to POST to the Google Sheet. Set API_SECRET in Cloudflare to enable writes.
 */
export function isAuthorized(headers: Headers, apiSecret: string | undefined): boolean {
  if (!apiSecret) {
    console.error("API_SECRET is not configured — refusing write");
    return false;
  }
  return headers.get("x-api-key") === apiSecret;
}
