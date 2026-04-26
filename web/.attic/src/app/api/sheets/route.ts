import { NextRequest, NextResponse } from "next/server";
import { getSheetData } from "@/lib/sheets";

export async function GET(req: NextRequest) {
  const tab = req.nextUrl.searchParams.get("tab") || "Overview";
  try {
    const data = await getSheetData(tab);
    return NextResponse.json(data, {
      headers: { "Cache-Control": "s-maxage=300, stale-while-revalidate" },
    });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
