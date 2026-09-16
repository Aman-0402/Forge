// Visual copy of dsaclone/src/pages/Login.tsx, wired to Forge's real auth API and
// PasswordInput (eye toggle) in place of the original decorative plain <input>.
import { useState, type FormEvent } from "react";
import { motion } from "framer-motion";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { errorMessage } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { homeFor } from "../../auth/guards";
import PasswordInput from "../../components/PasswordInput";

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: "easeOut" as const } },
};

const fieldStyle = {
  padding: "12px 16px",
  borderRadius: "8px",
  border: "1px solid rgba(255, 255, 255, 0.1)",
  background: "rgba(255, 255, 255, 0.05)",
  color: "var(--text-primary)",
  outline: "none",
};

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to={homeFor(user.role)} replace />;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const me = await login(email, password);
      navigate(homeFor(me.role), { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <motion.section
      initial="hidden"
      animate="visible"
      variants={fadeUp}
      style={{ maxWidth: "480px", margin: "40px auto 120px" }}
    >
      <div className="premium-box" style={{ padding: "40px" }}>
        <h2 className="section-title" style={{ textAlign: "center", marginBottom: "8px" }}>
          Welcome Back
        </h2>
        <p className="section-subtitle" style={{ textAlign: "center", marginBottom: "32px" }}>
          Log in to your account to continue
        </p>

        <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <label style={{ color: "var(--text-secondary)", fontSize: "14px", fontWeight: 500 }}>
              Email Address
            </label>
            <input
              type="email"
              placeholder="name@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              style={fieldStyle}
            />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <label style={{ color: "var(--text-secondary)", fontSize: "14px", fontWeight: 500 }}>
                Password
              </label>
              <Link
                to="/forgot-password"
                style={{ color: "var(--accent-primary)", fontSize: "12px", textDecoration: "none" }}
              >
                Forgot Password?
              </Link>
            </div>
            <PasswordInput
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          {error && <p className="error" style={{ margin: 0 }}>{error}</p>}

          <button type="submit" className="btn btn-primary" disabled={busy} style={{ padding: "16px", marginTop: "16px" }}>
            {busy ? "Logging in…" : "Log In"}
          </button>
        </form>

        <p style={{ textAlign: "center", marginTop: "24px", color: "var(--text-secondary)", fontSize: "14px" }}>
          Don't have an account?{" "}
          <Link to="/register" style={{ color: "var(--accent-primary)", textDecoration: "none", fontWeight: 500 }}>
            Sign up free
          </Link>
        </p>
      </div>
    </motion.section>
  );
}
