import { NextRequest, NextResponse } from "next/server";
import { appendRow } from "@/lib/sheets";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { tripName, from, to, goDate, backDate, preferDepart, preferArrive, addedBy } = body;

    if (!tripName || !from || !to || !goDate || !backDate || !addedBy) {
      return NextResponse.json({ error: "Missing fields" }, { status: 400 });
    }

    await appendRow("Config", [
      tripName, from, to, goDate, backDate,
      preferDepart || "12:00", preferArrive || "18:00",
      "Yes", addedBy, "",
    ]);

    return NextResponse.json({ ok: true });
  } catch (e: unknown) {
    const message = e instanceof Error ? e.message : "Unknown error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
