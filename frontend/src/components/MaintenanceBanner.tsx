import type { SiteSettings } from "../api/public";
import { useSiteSettings } from "../hooks/useSiteSettings";

/** Backend-controlled: admins toggle this from Site settings, no deploy needed.
 *
 * Pass `settings` when the caller already fetched it (avoids a duplicate request and,
 * more importantly, avoids two independent fetches resolving at different times —
 * MarketingLayout measures this banner's rendered height off the same `settings` it
 * passes in, so both update in the same render). Standalone callers can omit it. */
export default function MaintenanceBanner({ settings: given }: { settings?: SiteSettings | null }) {
  const fetched = useSiteSettings(given === undefined);
  const settings = given !== undefined ? given : fetched;
  if (!settings?.maintenance_mode) return null;
  return (
    <div className="notice warn" role="status" style={{ borderRadius: 0, margin: 0 }}>
      {settings.maintenance_message || "This site is undergoing maintenance."}
    </div>
  );
}
