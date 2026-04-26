import { SignJWT, importPKCS8 } from "jose";

const SHEET_ID = process.env.GOOGLE_SHEET_ID!;
const TOKEN_URL = "https://oauth2.googleapis.com/token";
const SHEETS_BASE = "https://sheets.googleapis.com/v4/spreadsheets";
const SCOPE = "https://www.googleapis.com/auth/spreadsheets";

let cachedToken: { value: string; exp: number } | null = null;

interface ServiceAccountCreds {
  client_email: string;
  private_key: string;
  token_uri?: string;
}

function readCreds(): ServiceAccountCreds {
  const raw = process.env.GOOGLE_CREDENTIALS_JSON || "{}";
  return JSON.parse(raw) as ServiceAccountCreds;
}

async function getAccessToken(): Promise<string> {
  const now = Math.floor(Date.now() / 1000);
  if (cachedToken && cachedToken.exp - 30 > now) {
    return cachedToken.value;
  }

  const creds = readCreds();
  if (!creds.client_email || !creds.private_key) {
    throw new Error("GOOGLE_CREDENTIALS_JSON missing client_email or private_key");
  }

  const privateKey = await importPKCS8(creds.private_key, "RS256");
  const assertion = await new SignJWT({ scope: SCOPE })
    .setProtectedHeader({ alg: "RS256", typ: "JWT" })
    .setIssuer(creds.client_email)
    .setAudience(creds.token_uri || TOKEN_URL)
    .setIssuedAt(now)
    .setExpirationTime(now + 3600)
    .sign(privateKey);

  const body = new URLSearchParams({
    grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
    assertion,
  });

  const resp = await fetch(creds.token_uri || TOKEN_URL, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!resp.ok) {
    throw new Error(`Token exchange failed: ${resp.status} ${await resp.text()}`);
  }
  const json = (await resp.json()) as { access_token: string; expires_in: number };
  cachedToken = { value: json.access_token, exp: now + json.expires_in };
  return cachedToken.value;
}

async function sheetsFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const token = await getAccessToken();
  return fetch(`${SHEETS_BASE}/${SHEET_ID}${path}`, {
    ...init,
    headers: {
      ...(init.headers || {}),
      Authorization: `Bearer ${token}`,
    },
  });
}

export async function getSheetData(tab: string): Promise<Record<string, string>[]> {
  const range = encodeURIComponent(`${tab}!A:Z`);
  const resp = await sheetsFetch(`/values/${range}`);
  if (!resp.ok) {
    throw new Error(`Sheets read failed: ${resp.status} ${await resp.text()}`);
  }
  const json = (await resp.json()) as { values?: string[][] };
  const rows = json.values || [];
  if (rows.length < 2) return [];
  const headers = rows[0];
  return rows.slice(1).map((row) => {
    const obj: Record<string, string> = {};
    headers.forEach((h, i) => {
      obj[h] = row[i] || "";
    });
    return obj;
  });
}

export async function appendRow(tab: string, values: string[]): Promise<void> {
  const range = encodeURIComponent(`${tab}!A:Z`);
  const resp = await sheetsFetch(
    `/values/${range}:append?valueInputOption=USER_ENTERED`,
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ values: [values] }),
    },
  );
  if (!resp.ok) {
    throw new Error(`Sheets append failed: ${resp.status} ${await resp.text()}`);
  }
}
