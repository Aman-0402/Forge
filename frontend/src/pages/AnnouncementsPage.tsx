import { useState, type FormEvent } from "react";
import { listDepartments } from "../api/admin";
import { errorMessage } from "../api/client";
import { listCourses } from "../api/courses";
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
import { confirmDialog } from "../utils/notify";

const AUDIENCE_LABEL: Record<Audience, string> = {
  all: "Everyone",
  faculty: "All faculty",
  students: "All students",
  department: "A department",
  course: "A course",
};

export default function AnnouncementsPage() {
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const list = useLoad(() => listAnnouncements({ page }), [page]);
  const canPost = user?.role === "admin" || user?.role === "faculty";

  async function onDelete(id: number) {
    if (!(await confirmDialog({ title: "Delete this announcement?", danger: true }))) return;
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
      <div className="page-head">
        <div>
          <div className="eyebrow">Updates</div>
          <h1>Announcements</h1>
        </div>
      </div>
      {canPost && <AnnouncementForm onCreated={list.reload} />}
      {(error || list.error) && <p className="error">{error || list.error}</p>}
      {list.data?.results.length === 0 && (
        <div className="empty">
          <strong>No announcements</strong>
          Posts for you, your department and your courses show up here.
        </div>
      )}
      <ul className="cards">
        {list.data?.results.map((a) => (
          <li key={a.id} className="card-item">
            <div className="card-head">
              <strong>{a.title}</strong>
              <span className="meta">
                {a.course_title ?? (a.department_code ? `Department ${a.department_code}` : AUDIENCE_LABEL[a.audience])}
                {" · "}
                {a.author_name ?? "System"} · {formatDate(a.published_at)}
                {a.expires_at && ` · until ${formatDate(a.expires_at)}`}
                {!a.delivered_at && new Date(a.published_at) > new Date() && " · Scheduled, not sent yet"}
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
  const courses = useLoad(
    () => listCourses({ page_size: 100 }).then((r) => r.results.filter((c) => c.can_manage)),
    [],
  );
  const audiences: Audience[] = isFaculty
    ? [...(user?.department ? (["department"] as Audience[]) : []), "course"]
    : ["all", "students", "faculty", "department", "course"];

  const [form, setForm] = useState({
    title: "",
    body: "",
    audience: audiences[0],
    department: isFaculty && user?.department ? String(user.department.id) : "",
    course: "",
    published_at: "",
    expires_at: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

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
        course: form.audience === "course" ? Number(form.course) : null,
        ...(form.published_at ? { published_at: new Date(form.published_at).toISOString() } : {}),
        expires_at: form.expires_at ? new Date(form.expires_at).toISOString() : null,
      });
      setForm({ ...form, title: "", body: "", published_at: "", expires_at: "" });
      onCreated();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel" onSubmit={onSubmit}>
      <h2>Post an announcement</h2>
      <div className="grid">
        <label>
          Title
          <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
        </label>
        <label>
          Send to
          <select
            value={form.audience}
            onChange={(e) => setForm({ ...form, audience: e.target.value as Audience })}
          >
            {audiences.map((value) => (
              <option key={value} value={value}>
                {AUDIENCE_LABEL[value]}
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
        {form.audience === "course" && (
          <label>
            Course
            <select value={form.course} onChange={(e) => setForm({ ...form, course: e.target.value })} required>
              <option value="">Choose…</option>
              {courses.data?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code ? `${c.code} — ` : ""}
                  {c.title}
                </option>
              ))}
            </select>
          </label>
        )}
        <label>
          Publish at (optional)
          <input
            type="datetime-local"
            value={form.published_at}
            onChange={(e) => setForm({ ...form, published_at: e.target.value })}
          />
        </label>
        <label>
          Hide after (optional)
          <input
            type="datetime-local"
            value={form.expires_at}
            onChange={(e) => setForm({ ...form, expires_at: e.target.value })}
          />
        </label>
      </div>
      <label>
        Message
        <textarea rows={4} value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} required />
      </label>
      {error && <p className="error">{error}</p>}
      <div className="row">
        <button disabled={busy}>{busy ? "Posting…" : form.published_at ? "Schedule announcement" : "Post announcement"}</button>
      </div>
    </form>
  );
}
