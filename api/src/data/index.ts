import type { FlightDataSource } from "./adapter";
import { SheetsDataSource } from "./sheets";

interface Env {
  DATA_SOURCE?: string;
  GOOGLE_SHEET_ID: string;
  GOOGLE_CREDENTIALS_JSON: string;
}

export function createDataSource(env: Env): FlightDataSource {
  const source = (env.DATA_SOURCE || "sheets").toLowerCase();
  switch (source) {
    case "sheets":
      return new SheetsDataSource(env);
    // case "d1":  // Phase B
    //   return new D1DataSource(env);
    default:
      throw new Error(`Unknown DATA_SOURCE: ${source}`);
  }
}
