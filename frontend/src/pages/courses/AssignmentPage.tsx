import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { errorMessage } from "../../api/client";
import {
  getAssignment,
  getCourse,
  gradeSubmission,
  listSubmissions,
  submitAssignment,
  type Submission,
} from "../../api/courses";
import Pager from "../../components/Pager";
import { useLoad } from "../../hooks/useLoad";
import { formatDate } from "../../utils/format";

export default function AssignmentPage() {
  const id = Number(useParams().id);
  const assignment = useLoad(() => getAssignment(id), [id]);
  const course = useLoad(
    () => (assignment.data ? getCourse(assignment.data.course) : Promise.resolve(null)),
    [assignment.data?.course],
  );
  const a = assignment.data;

  if (assignment.error) return <p className="error">{assignment.error}</p>;
  if (!a) return <p className="hint">Loading assignment…</p>;

  const manager = course.data?.can_manage ?? false;
  const overdue = a.due_at ? new Date(a.due_at) < new Date() : false;

  return (
    <>
      <div className="eyebrow">
        <Link to={`/courses/${a.course}?tab=assignments`}>{course.data?.title ?? "Course"}</Link> / Assignment
      </div>
      <div className="page-head">
        <h1>{a.title}</h1>
        <div className="row">
          <span className="chip">Due {formatDate(a.due_at)}</span>
          <span className="chip mono">{Number(a.max_marks)} marks</span>
          {a.allow_late && <span className="chip">Late work accepted</span>}
        </div>
      </div>

      <section className="panel">
        {a.description ? <p className="pre">{a.description}</p> : <p className="hint">No written instructions.</p>}
        {a.attachment && (
          <a className="button secondary small" href={a.attachment} target="_blank" rel="noreferrer">
            Download brief
          </a>
        )}
      </section>

      {course.data && !manager && <StudentSubmission assignmentId={a.id} closed={overdue && !a.allow_late} />}
      {manager && <GradingTable assignmentId={a.id} maxMarks={a.max_marks} />}
    </>
  );
}

function StudentSubmission({ assignmentId, closed }: { assignmentId: number; closed: boolean }) {
  const mine = useLoad(() => listSubmissions(assignmentId), [assignmentId]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const sub = mine.data?.results[0];

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const file = form.get("file") as File | null;
    if (!file || file.size === 0) form.delete("file");
    setError("");
    setBusy(true);
    try {
      await submitAssignment(assignmentId, form);
      e.currentTarget?.reset();
      mine.reload();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      {sub && (
        <section className="panel">
          <div className="panel-head">
            <h2>Your submission</h2>
            <div className="row">
              {sub.is_late && <span className="status late">Late</span>}
              {sub.graded_at ? (
                <span className="status completed">
                  {Number(sub.marks)} / {Number(sub.max_marks)}
                </span>
              ) : (
                <span className="status active">Awaiting grade</span>
              )}
            </div>
          </div>
          <p className="meta">Submitted {formatDate(sub.submitted_at)}</p>
          {sub.text && <p className="pre">{sub.text}</p>}
          {sub.file && (
            <a href={sub.file} target="_blank" rel="noreferrer">
              Open attached file
            </a>
          )}
          {sub.feedback && (
            <div className="notice">
              <strong>Feedback:</strong> <span className="pre">{sub.feedback}</span>
            </div>
          )}
        </section>
      )}

      {!sub?.graded_at && (
        <form className="panel" onSubmit={onSubmit}>
          <h2>{sub ? "Replace your submission" : "Submit your work"}</h2>
          {closed ? (
            <p className="notice warn">The due date has passed and late work is not accepted.</p>
          ) : (
            <>
              <label>
                Answer
                <textarea name="text" rows={6} defaultValue={sub?.text ?? ""} />
              </label>
              <label>
                File
                <input name="file" type="file" />
              </label>
              <p className="hint">You can resubmit until your work is graded.</p>
              {error && <p className="error">{error}</p>}
              <div className="row">
                <button disabled={busy}>{busy ? "Submitting…" : sub ? "Resubmit" : "Submit"}</button>
              </div>
            </>
          )}
        </form>
      )}
    </>
  );
}

function GradingTable({ assignmentId, maxMarks }: { assignmentId: number; maxMarks: string }) {
  const [graded, setGraded] = useState("");
  const [page, setPage] = useState(1);
  const list = useLoad(() => listSubmissions(assignmentId, { graded, page }), [assignmentId, graded, page]);

  return (
    <section>
      <div className="panel-head">
        <h2>Submissions</h2>
        <select
          value={graded}
          onChange={(e) => {
            setGraded(e.target.value);
            setPage(1);
          }}
          aria-label="Filter submissions"
        >
          <option value="">All</option>
          <option value="false">Needs grading</option>
          <option value="true">Graded</option>
        </select>
      </div>
      {list.error && <p className="error">{list.error}</p>}
      {list.data?.results.length === 0 && (
        <div className="empty">
          <strong>Nothing here</strong>
          Submissions appear as students hand in work.
        </div>
      )}
      {list.data && list.data.results.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Student</th>
                <th>Submitted</th>
                <th>Work</th>
                <th>Grade</th>
              </tr>
            </thead>
            <tbody>
              {list.data.results.map((s) => (
                <GradeRow key={s.id} submission={s} maxMarks={maxMarks} onSaved={list.reload} />
              ))}
            </tbody>
          </table>
        </div>
      )}
      {list.data && <Pager page={page} count={list.data.count} onPage={setPage} />}
    </section>
  );
}

function GradeRow({
  submission: s,
  maxMarks,
  onSaved,
}: {
  submission: Submission;
  maxMarks: string;
  onSaved: () => void;
}) {
  const [marks, setMarks] = useState(s.marks ? String(Number(s.marks)) : "");
  const [feedback, setFeedback] = useState(s.feedback);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function save(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await gradeSubmission(s.id, marks, feedback);
      onSaved();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <tr>
      <td>
        {s.student_detail.name}
        <div className="meta">
          {s.student_detail.email}
          {s.student_detail.roll_number && ` · ${s.student_detail.roll_number}`}
        </div>
      </td>
      <td>
        {formatDate(s.submitted_at)}
        {s.is_late && (
          <>
            {" "}
            <span className="status late">Late</span>
          </>
        )}
      </td>
      <td>
        {s.text && <div className="pre">{s.text.length > 180 ? `${s.text.slice(0, 180)}…` : s.text}</div>}
        {s.file && (
          <a href={s.file} target="_blank" rel="noreferrer">
            Open file
          </a>
        )}
      </td>
      <td>
        <form className="inline-form" onSubmit={save}>
          <input
            type="number"
            min="0"
            max={Number(maxMarks)}
            step="0.5"
            value={marks}
            onChange={(e) => setMarks(e.target.value)}
            required
            aria-label="Marks"
          />
          <span className="meta">/ {Number(maxMarks)}</span>
          <input value={feedback} onChange={(e) => setFeedback(e.target.value)} placeholder="Feedback" aria-label="Feedback" />
          <button className="small" disabled={busy}>
            {s.graded_at ? "Update" : "Save grade"}
          </button>
          {error && <p className="error">{error}</p>}
        </form>
      </td>
    </tr>
  );
}
