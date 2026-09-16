import { useState, type FormEvent } from "react";
import { listDepartments } from "../api/admin";
import { errorMessage } from "../api/client";
import {
  createAnnouncement,
  deleteAnnouncement,
  listAnnouncements,
  type Audience,
} from "../api/notifications";
import { useAuth } from "../auth/AuthContext";
import Pager from "../components/Pager";
import { useLoad } from "../hooks/useLoad";
import { formatDate } from "../utils/format";

const AUDIENCE_LABEL: Record<Audience, string> = {
  all: "Everyone",
  faculty: "Faculty",
  students: "Students",
  department: "Department",
};

export default function AnnouncementsPage() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const list = useLoad(() => listAnnouncements({ page }), [page]);
  const canPost = user?.role === "admin" || user?.role === "faculty";

  async function onDelete(id: number) {
    if (!window.confirm("Delete this announcement?")) return;
    setError("");
    try {
      await deleteAnnouncement(id);
      list.reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <>
      <h1>Announcements</h1>
      {canPost && <AnnouncementForm onCreated={list.reload} />}
      {(error || list.error) && <p className="error">{error || list.error}</p>}
      {list.data?.results.length === 0 && <p>No announcements.</p>}
      <ul className="cards">
        {list.data?.results.map((a) => (
          <li key={a.id} className="card-item">
            <div className="card-head">
              <strong>{a.title}</strong>
              <span className="meta">
                {AUDIENCE_LABEL[a.audience]}
                {a.department_code && ` (${a.department_code})`} · {a.author_name ?? "system"} ·{" "}
                {formatDate(a.published_at)}
                {a.expires_at && ` · expires ${formatDate(a.expires_at)}`}
              </span>
            </div>
            <p className="pre">{a.body}</p>
            {(user?.role === "admin" || a.author === user?.id) && (
              <button className="link danger" onClick={() => onDelete(a.id)}>
                Delete
              </button>
            )}
          </li>
        ))}
      </ul>
      {list.data && <Pager page={page} count={list.data.count} onPage={setPage} />}
    </>
  );
}

function AnnouncementForm({ onCreated }: { onCreated: () => void }) {
  const { user } = useAuth();
  const isFaculty = user?.role === "faculty";
  const departments = useLoad(listDepartments, []);
  const [form, setForm] = useState({
    title: "",
    body: "",
    audience: (isFaculty ? "department" : "all") as Audience,
    department: isFaculty && user?.department ? String(user.department.id) : "",
    expires_at: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (isFaculty && !user?.department) {
    return (
      <p className="notice">
        You need a department to post announcements. Ask an admin to assign one.
      </p>
    );
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await createAnnouncement({
        title: form.title,
        body: form.body,
        audience: form.audience,
        department: form.audience === "department" ? Number(form.department) : null,
        expires_at: form.expires_at ? new Date(form.expires_at).toISOString() : null,
      });
      setForm({ ...form, title: "", body: "", expires_at: "" });
      onCreated();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel" onSubmit={onSubmit}>
      <h2>New announcement</h2>
      <div className="grid">
        <label>
          Title
          <input
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            required
          />
        </label>
        <label>
          Audience
          <select
            value={form.audience}
            disabled={isFaculty}
            onChange={(e) => setForm({ ...form, audience: e.target.value as Audience })}
          >
            {Object.entries(AUDIENCE_LABEL).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        {form.audience === "department" && (
          <label>
            Department
            <select
              value={form.department}
              disabled={isFaculty}
              onChange={(e) => setForm({ ...form, department: e.target.value })}
              required
            >
              <option value="">Choose…</option>
              {departments.data?.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.code} — {d.name}
                </option>
              ))}
            </select>
          </label>
        )}
        <label>
          Expires (optional)
          <input
            type="datetime-local"
            value={form.expires_at}
            onChange={(e) => setForm({ ...form, expires_at: e.target.value })}
          />
        </label>
      </div>
      <label>
        Message
        <textarea
          rows={4}
          value={form.body}
          onChange={(e) => setForm({ ...form, body: e.target.value })}
          required
        />
      </label>
      {error && <p className="error">{error}</p>}
      <button disabled={busy}>{busy ? "Posting…" : "Post announcement"}</button>
    </form>
  );
}
