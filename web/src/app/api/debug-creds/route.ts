import { NextResponse } from "next/server";

// TEMPORARY: diagnostic endpoint to verify GOOGLE_CREDENTIALS_JSON env shape.
// Returns no secret material. Delete after the credential pipeline is verified.
export async function GET() {
  const raw = process.env.GOOGLE_CREDENTIALS_JSON || "";
  const len = raw.length;
  const first40 = raw.slice(0, 40);
  const last20 = raw.slice(-20);
  let parsed: unknown = null;
  let parseError: string | null = null;
  try {
    parsed = JSON.parse(raw);
  } catch (e) {
    parseError = e instanceof Error ? e.message : String(e);
  }

  const isObject = typeof parsed === "object" && parsed !== null && !Array.isArray(parsed);
  const keys = isObject ? Object.keys(parsed as Record<string, unknown>).sort() : null;
  const hasClientEmail =
    isObject && "client_email" in (parsed as Record<string, unknown>);
  const clientEmailDomain =
    hasClientEmail && typeof (parsed as Record<string, string>).client_email === "string"
      ? (parsed as Record<string, string>).client_email.split("@")[1]
      : null;
  const privateKeyMeta =
    isObject && "private_key" in (parsed as Record<string, unknown>)
      ? {
          length: String((parsed as Record<string, string>).private_key).length,
          startsWithBegin: String(
            (parsed as Record<string, string>).private_key,
          ).startsWith("-----BEGIN"),
          containsLiteralBackslashN:
            String((parsed as Record<string, string>).private_key).includes("\\n"),
          containsRealNewline:
            String((parsed as Record<string, string>).private_key).includes("\n"),
        }
      : null;

  return NextResponse.json({
    env_GOOGLE_SHEET_ID_set: Boolean(process.env.GOOGLE_SHEET_ID),
    env_API_SECRET_set: Boolean(process.env.API_SECRET),
    env_GOOGLE_CREDENTIALS_JSON: {
      length: len,
      first40,
      last20,
      parseError,
      parsed_type: typeof parsed,
      isObject,
      keys,
      hasClientEmail,
      clientEmailDomain,
      privateKeyMeta,
    },
  });
}
