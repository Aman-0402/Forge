import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { register } from "../api/auth";
import { errorMessage } from "../api/client";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "", first_name: "", last_name: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

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
    <main className="card">
      <h1>Student registration</h1>
      <form onSubmit={onSubmit}>
        <label>
          First name
          <input value={form.first_name} onChange={set("first_name")} />
        </label>
        <label>
          Last name
          <input value={form.last_name} onChange={set("last_name")} />
        </label>
        <label>
          Email
          <input type="email" value={form.email} onChange={set("email")} required />
        </label>
        <label>
          Password
          <input type="password" value={form.password} onChange={set("password")} required />
        </label>
        {error && <p className="error">{error}</p>}
        <button disabled={busy}>{busy ? "Creating…" : "Create account"}</button>
      </form>
      <p>
        Have an account? <Link to="/login">Login</Link>
      </p>
    </main>
  );
}
