import { useEffect, useState } from "react";
import { getSiteSettings, updateSiteSettings, type SiteSettings } from "../../api/admin";
import { errorMessage } from "../../api/client";
import { toast } from "../../utils/notify";

export default function SiteSettingsPage() {
  const [settings, setSettings] = useState<SiteSettings | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getSiteSettings()
      .then(setSettings)
      .catch((err) => setError(errorMessage(err)));
  }, []);

  async function save(patch: Partial<SiteSettings>) {
    if (!settings) return;
    setError("");
    setBusy(true);
    try {
      setSettings(await updateSiteSettings(patch));
      toast.success("Saved.");
    } catch (err) {
      toast.error(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  if (!settings) {
    return (
      <>
        <h1>Site settings</h1>
        {error ? <p className="error">{error}</p> : <p className="hint">Loading…</p>}
      </>
    );
  }

  return (
    <>
      <h1>Site settings</h1>
      <p className="hint">
        These control what visitors and the app can do right now. Changes take effect immediately
        for everyone, no deploy needed.
      </p>
      {error && <p className="error">{error}</p>}

      <div className="panel">
        <h2>Registration</h2>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={settings.registration_open}
            disabled={busy}
            onChange={(e) => save({ registration_open: e.target.checked })}
          />
          Allow new students to sign up at /register
        </label>
        {!settings.registration_open && (
          <p className="hint">
            Self-registration is closed. Admins can still create accounts from Users.
          </p>
        )}
      </div>

      <div className="panel">
        <h2>Maintenance banner</h2>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={settings.maintenance_mode}
            disabled={busy}
            onChange={(e) => save({ maintenance_mode: e.target.checked })}
          />
          Show a maintenance banner site-wide
        </label>
        <label>
          Banner message
          <textarea
            rows={3}
            value={settings.maintenance_message}
            disabled={busy}
            onChange={(e) => setSettings({ ...settings, maintenance_message: e.target.value })}
            onBlur={() => save({ maintenance_message: settings.maintenance_message })}
          />
        </label>
      </div>
    </>
  );
}
