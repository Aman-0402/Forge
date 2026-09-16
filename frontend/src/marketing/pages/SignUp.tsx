// Visual copy of dsaclone/src/pages/SignUp.tsx, wired to Forge's real register API
// and PasswordInput (eye toggle) in place of the original decorative plain <input>.
import { useState, type FormEvent } from "react";
import { motion } from "framer-motion";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../../api/auth";
import { errorMessage } from "../../api/client";
import PasswordInput from "../../components/PasswordInput";
import { useSiteSettings } from "../../hooks/useSiteSettings";

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
  width: "100%",
};

export default function SignUp() {
  const navigate = useNavigate();
  const settings = useSiteSettings();
  const [form, setForm] = useState({ first_name: "", last_name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const registrationClosed = settings?.registration_open === false;

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [key]: e.target.value });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await register(form);
      navigate("/login", { replace: true });
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
          Create an Account
        </h2>
        <p className="section-subtitle" style={{ textAlign: "center", marginBottom: "32px" }}>
          Join DSA Forge and accelerate your career
        </p>

        {registrationClosed ? (
          <p style={{ textAlign: "center", color: "var(--text-secondary)" }}>
            New sign-ups are paused right now. Please check back soon, or{" "}
            <Link to="/contact" style={{ color: "var(--accent-primary)" }}>
              contact us
            </Link>{" "}
            if it's urgent.
          </p>
        ) : (
        <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          <div className="auth-name-row" style={{ display: "flex", gap: "16px" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", flex: 1 }}>
              <label style={{ color: "var(--text-secondary)", fontSize: "14px", fontWeight: 500 }}>
                First Name
              </label>
              <input type="text" placeholder="John" value={form.first_name} onChange={set("first_name")} style={fieldStyle} />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px", flex: 1 }}>
              <label style={{ color: "var(--text-secondary)", fontSize: "14px", fontWeight: 500 }}>
                Last Name
              </label>
              <input type="text" placeholder="Doe" value={form.last_name} onChange={set("last_name")} style={fieldStyle} />
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <label style={{ color: "var(--text-secondary)", fontSize: "14px", fontWeight: 500 }}>
              Email Address
            </label>
            <input
              type="email"
              placeholder="name@example.com"
              value={form.email}
              onChange={set("email")}
              required
              style={fieldStyle}
            />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <label style={{ color: "var(--text-secondary)", fontSize: "14px", fontWeight: 500 }}>
              Password
            </label>
            <PasswordInput
              placeholder="••••••••"
              value={form.password}
              onChange={set("password")}
              autoComplete="new-password"
              required
            />
          </div>

          {error && <p className="error" style={{ margin: 0 }}>{error}</p>}

          <button type="submit" className="btn btn-primary" disabled={busy} style={{ padding: "16px", marginTop: "16px" }}>
            {busy ? "Creating…" : "Sign Up"}
          </button>
        </form>
        )}

        <p style={{ textAlign: "center", marginTop: "24px", color: "var(--text-secondary)", fontSize: "14px" }}>
          Already have an account?{" "}
          <Link to="/login" style={{ color: "var(--accent-primary)", textDecoration: "none", fontWeight: 500 }}>
            Log in
          </Link>
        </p>
      </div>
    </motion.section>
  );
}
