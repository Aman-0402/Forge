import { useEffect, useState } from "react";
import { getSiteSettings, type SiteSettings } from "../api/public";

/** Backend-controlled switches (registration open, maintenance banner). Best-effort:
 * if the request fails, callers get null and should assume nothing is restricted.
 * Pass `enabled: false` to skip the fetch (e.g. a child that received the value via
 * props from a parent that already fetched it). */
export function useSiteSettings(enabled = true) {
  const [settings, setSettings] = useState<SiteSettings | null>(null);

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    getSiteSettings()
      .then((s) => !cancelled && setSettings(s))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [enabled]);

  return settings;
}
