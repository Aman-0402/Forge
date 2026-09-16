import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { changePassword } from "../api/auth";
import { errorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { homeFor } from "../auth/guards";
import PasswordInput from "../components/PasswordInput";

export default function ChangePasswordPage() {
  const { user, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (newPassword !== confirm) {
      setError("New passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      await changePassword(oldPassword, newPassword);
      await refreshUser();
      navigate(user ? homeFor(user.role) : "/", { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="narrow">
      <h1>Change password</h1>
      {user?.must_change_password && (
        <p className="notice">You signed in with a temporary password. Choose a new one to continue.</p>
      )}
      <form onSubmit={onSubmit}>
        <label>
          Current password
          <PasswordInput
            value={oldPassword}
            onChange={(e) => setOldPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        <label>
          New password
          <PasswordInput
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            autoComplete="new-password"
            required
          />
        </label>
        <label>
          Confirm new password
          <PasswordInput
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            autoComplete="new-password"
            required
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button disabled={busy}>{busy ? "Saving…" : "Change password"}</button>
      </form>
    </section>
  );
}
