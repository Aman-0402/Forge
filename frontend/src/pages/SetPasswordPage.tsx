import { useState, type FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { setPasswordFromLink } from "../api/auth";
import { errorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import AuthFrame from "../components/AuthFrame";
import PasswordInput from "../components/PasswordInput";

export default function SetPasswordPage() {
  const [params] = useSearchParams();
  const uid = params.get("uid") ?? "";
  const token = params.get("token") ?? "";
  const { refreshUser } = useAuth();
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      await setPasswordFromLink(uid, token, password);
      await refreshUser();
      navigate("/", { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthFrame>
      <div className="eyebrow">Account access</div>
      <h1>Choose a password</h1>
      {!uid || !token ? (
        <p className="error">
          This link is incomplete. Open the link from your email again, or{" "}
          <Link to="/forgot-password">request a new one</Link>.
        </p>
      ) : (
        <form onSubmit={onSubmit}>
          <label>
            New password
            <PasswordInput
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              required
            />
          </label>
          <label>
            Confirm password
            <PasswordInput
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              autoComplete="new-password"
              required
            />
          </label>
          {error && (
            <p className="error">
              {error} {error.includes("expired") && <Link to="/forgot-password">Request a new link</Link>}
            </p>
          )}
          <button disabled={busy}>{busy ? "Saving…" : "Save password and sign in"}</button>
        </form>
      )}
    </AuthFrame>
  );
}
