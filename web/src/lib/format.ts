const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const MONTH_TO_NUM: Record<string, string> = {
  Jan:"01", Feb:"02", Mar:"03", Apr:"04", May:"05", Jun:"06",
  Jul:"07", Aug:"08", Sep:"09", Oct:"10", Nov:"11", Dec:"12",
};

export function formatThb(value: number): string {
  return `฿${value.toLocaleString("en-US")}`;
}

export function isoToShortDate(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return iso;
  const day = parseInt(m[3], 10).toString();
  const month = MONTHS[parseInt(m[2], 10) - 1] ?? "";
  return `${day.padStart(2, "0")} ${month}`;
}

export function shortDateToIso(label: string, year: number = new Date().getFullYear()): string {
  const [day, mon] = label.split(" ");
  if (!day || !mon) return label;
  const month = MONTH_TO_NUM[mon] ?? "01";
  return `${year}-${month}-${day.padStart(2, "0")}`;
}

export function formatShortDate(iso: string): string {
  return isoToShortDate(iso);
}

export function formatDuration(totalMinutes: number): string {
  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;
  return `${h}h ${m}m`;
}
