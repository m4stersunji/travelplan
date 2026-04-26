import { useEffect } from "react";

export function SWRegister() {
  useEffect(() => {
    if (
      typeof window === "undefined" ||
      !("serviceWorker" in navigator) ||
      window.location.hostname === "localhost"
    ) return;
    navigator.serviceWorker
      .register("/sw.js", { scope: "/" })
      .catch((e) => console.warn("SW register failed", e));
  }, []);
  return null;
}
