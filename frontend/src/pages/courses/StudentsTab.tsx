import { useState, type FormEvent } from "react";
import { listDepartments } from "../../api/admin";
import { errorMessage } from "../../api/client";
import {
  bulkEnroll,
  courseEnrollments,
  courseProgress,
  removeEnrollment,
  type Course,
} from "../../api/courses";
import { StatusChip } from "../../components/CourseCard";
import Pager from "../../components/Pager";
import TemperBar from "../../components/TemperBar";
import { useLoad } from "../../hooks/useLoad";
import { formatDate } from "../../utils/format";

export default function StudentsTab({ course }: { course: Course }) {
  const [view, setView] = useState<"progress" | "roster">("progress");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const progress = useLoad(
    () => (view === "progress" ? courseProgress(course.id, { page }) : Promise.resolve(null)),
    [course.id, view, page],
  );
  const roster = useLoad(
    () =>
      view === "roster" ? courseEnrollments(course.id, { search, page }) : Promise.resolve(null),
    [course.id, view, search, page],
  );

  async function remove(id: number, email: string) {
    if (!window.confirm(`Remove ${email} from this course? Their progress is kept.`)) return;
    setError("");
    try {
      await removeEnrollment(id);
      roster.reload();
      progress.reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <>
      {course.status === "published" ? (
        <AddStudents
          courseId={course.id}
          onDone={(msg) => {
            setMessage(msg);
            roster.reload();
            progress.reload();
          }}
        />
      ) : (
        <p className="notice warn">Publish the course before adding students.</p>
      )}
      {message && <p className="notice">{message}</p>}
      {error && <p className="error">{error}</p>}

      <div className="toolbar">
        <div className="tabs">
          <button aria-selected={view === "progress"} onClick={() => { setView("progress"); setPage(1); }}>
            Progress
          </button>
          <button aria-selected={view === "roster"} onClick={() => { setView("roster"); setPage(1); }}>
            Roster
          </button>
        </div>
        <span className="spacer" />
        {view === "roster" && (
          <input
            type="search"
            placeholder="Search name, email or roll number"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        )}
      </div>

      {view === "progress" && (
        <>
          {progress.error && <p className="error">{progress.error}</p>}
          {progress.data?.results.length === 0 && (
            <div className="empty">
              <strong>No active students</strong>
              Add students above to see their progress here.
            </div>
          )}
          {progress.data && progress.data.results.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Student</th>
                    <th>Roll no.</th>
                    <th>Progress</th>
                    <th className="num">Lessons</th>
                    <th>Status</th>
                    <th>Last activity</th>
                  </tr>
                </thead>
                <tbody>
                  {progress.data.results.map((r) => (
                    <tr key={r.id}>
                      <td>
                        {r.student_detail.name}
                        <div className="meta">{r.student_detail.email}</div>
                      </td>
                      <td className="mono">{r.student_detail.roll_number ?? "—"}</td>
                      <td>
                        <TemperBar value={r.progress_percent} label={`Progress of ${r.student_detail.name}`} />
                      </td>
                      <td className="num">
                        {r.completed_lessons}/{r.total_lessons}
                      </td>
                      <td>
                        <StatusChip status={r.status} />
                      </td>
                      <td>{formatDate(r.last_activity)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {progress.data && <Pager page={page} count={progress.data.count} onPage={setPage} />}
        </>
      )}

      {view === "roster" && (
        <>
          {roster.error && <p className="error">{roster.error}</p>}
          {roster.data && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Student</th>
                    <th>Batch</th>
                    <th>Joined</th>
                    <th>How</th>
                    <th>Status</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {roster.data.results.map((e) => (
                    <tr key={e.id} className={e.status === "dropped" ? "muted" : ""}>
                      <td>
                        {e.student_detail.name}
                        <div className="meta">{e.student_detail.email}</div>
                      </td>
                      <td>{e.student_detail.batch || "—"}</td>
                      <td>{formatDate(e.enrolled_at)}</td>
                      <td>{e.source}</td>
                      <td>
                        <StatusChip status={e.status} />
                      </td>
                      <td className="actions">
                        {e.status !== "dropped" && (
                          <button className="link danger" onClick={() => remove(e.id, e.student_detail.email)}>
                            Remove
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {roster.data && <Pager page={page} count={roster.data.count} onPage={setPage} />}
        </>
      )}
    </>
  );
}

function AddStudents({ courseId, onDone }: { courseId: number; onDone: (message: string) => void }) {
  const departments = useLoad(listDepartments, []);
  const [ids, setIds] = useState("");
  const [batch, setBatch] = useState("");
  const [department, setDepartment] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const student_ids = ids
        .split(/[\s,]+/)
        .map((s) => Number(s))
        .filter((n) => Number.isInteger(n) && n > 0);
      const result = await bulkEnroll(courseId, {
        student_ids,
        batch: batch.trim(),
        department: department ? Number(department) : null,
      });
      setIds("");
      setBatch("");
      setDepartment("");
      onDone(
        `Enrolled ${result.enrolled.length}. Already enrolled ${result.already_enrolled.length}.` +
          (result.invalid.length ? ` Skipped ${result.invalid.length} IDs that are not active students.` : ""),
      );
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel" onSubmit={onSubmit}>
      <h2>Add students</h2>
      <p className="hint">Use any combination. Everyone matching is enrolled and notified.</p>
      <div className="grid">
        <label>
          Student IDs
          <input value={ids} onChange={(e) => setIds(e.target.value)} placeholder="e.g. 12, 15, 18" />
        </label>
        <label>
          Whole batch
          <input value={batch} onChange={(e) => setBatch(e.target.value)} placeholder="e.g. 2026" />
        </label>
        <label>
          Whole department
          <select value={department} onChange={(e) => setDepartment(e.target.value)}>
            <option value="">None</option>
            {departments.data?.map((d) => (
              <option key={d.id} value={d.id}>
                {d.code} — {d.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="row">
        <button disabled={busy || !(ids.trim() || batch.trim() || department)}>
          {busy ? "Enrolling…" : "Enroll students"}
        </button>
      </div>
    </form>
  );
}
