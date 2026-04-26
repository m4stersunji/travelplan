const KEYS = {
  apiKey: "travelplan.apiKey",
  addedBy: "travelplan.addedBy",
} as const;

export function getStored(key: keyof typeof KEYS): string {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(KEYS[key]) ?? "";
}

export function setStored(key: keyof typeof KEYS, value: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(KEYS[key], value);
}

export function clearAllStored(): void {
  if (typeof window === "undefined") return;
  for (const v of Object.values(KEYS)) window.localStorage.removeItem(v);
}
