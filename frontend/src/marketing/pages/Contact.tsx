import { useState, type FormEvent } from "react";
import { motion } from "framer-motion";
import { sendContactMessage } from "../../api/public";
import { errorMessage } from "../../api/client";

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

export default function Contact() {
  const [form, setForm] = useState({ name: "", email: "", message: "" });
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm({ ...form, [key]: e.target.value });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await sendContactMessage(form);
      setSent(true);
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
      style={{ maxWidth: "600px", margin: "40px auto 120px" }}
    >
      <div className="glass-panel" style={{ padding: "40px", borderRadius: "16px" }}>
        <h2 className="section-title" style={{ textAlign: "center", marginBottom: "8px" }}>
          Contact Us
        </h2>
        <p className="section-subtitle" style={{ textAlign: "center" }}>
          Have questions? We'd love to hear from you.
        </p>

        {sent ? (
          <p style={{ textAlign: "center", color: "var(--text-secondary)", marginTop: "24px" }}>
            Thanks, {form.name.split(" ")[0] || "there"}. We got your message and will reply at{" "}
            {form.email} soon.
          </p>
        ) : (
          <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: "20px", marginTop: "24px" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              <label style={{ color: "var(--text-secondary)", fontSize: "14px", fontWeight: 500 }}>Name</label>
              <input
                type="text"
                placeholder="Your Name"
                value={form.name}
                onChange={set("name")}
                required
                style={fieldStyle}
              />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              <label style={{ color: "var(--text-secondary)", fontSize: "14px", fontWeight: 500 }}>Email</label>
              <input
                type="email"
                placeholder="your@email.com"
                value={form.email}
                onChange={set("email")}
                required
                style={fieldStyle}
              />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              <label style={{ color: "var(--text-secondary)", fontSize: "14px", fontWeight: 500 }}>Message</label>
              <textarea
                rows={5}
                placeholder="How can we help you?"
                value={form.message}
                onChange={set("message")}
                required
                style={{ ...fieldStyle, resize: "vertical" }}
              />
            </div>
            {error && <p className="error" style={{ margin: 0 }}>{error}</p>}
            <button type="submit" className="btn btn-primary" disabled={busy} style={{ padding: "16px", marginTop: "8px" }}>
              {busy ? "Sending…" : "Send Message"}
            </button>
          </form>
        )}
      </div>
    </motion.section>
  );
}
