import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { errorMessage } from "../../api/client";
import { createAssignment, deleteAssignment, listAssignments, type Course } from "../../api/courses";
import { useLoad } from "../../hooks/useLoad";
import { formatDate } from "../../utils/format";
import { confirmDialog } from "../../utils/notify";

export default function AssignmentsTab({ course }: { course: Course }) {
  const list = useLoad(() => listAssignments(course.id), [course.id]);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const manager = course.can_manage;

  async function remove(id: number, title: string) {
    if (!(await confirmDialog({ title: `Delete "${title}" and all its submissions?`, danger: true }))) return;
    try {
      await deleteAssignment(id);
      list.reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <>
      {manager && (
        <div className="panel-head">
          <p className="hint">Enrolled students are notified when you post an assignment.</p>
          {!creating && <button onClick={() => setCreating(true)}>New assignment</button>}
        </div>
      )}
      {creating && (
        <AssignmentForm
          courseId={course.id}
          onDone={() => {
            setCreating(false);
            list.reload();
          }}
          onCancel={() => setCreating(false)}
        />
      )}
      {(error || list.error) && <p className="error">{error || list.error}</p>}
      {list.data?.length === 0 && (
        <div className="empty">
          <strong>No assignments yet</strong>
          {manager ? "Post the first assignment for this course." : "Your instructor has not posted any work."}
        </div>
      )}
      {list.data && list.data.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Assignment</th>
                <th>Due</th>
                <th className="num">Marks</th>
                {manager ? (
                  <>
                    <th className="num">Submitted</th>
                    <th className="num">Graded</th>
                    <th />
                  </>
                ) : (
                  <th>Your work</th>
                )}
              </tr>
            </thead>
            <tbody>
              {list.data.map((a) => {
                const overdue = a.due_at && new Date(a.due_at) < new Date();
                return (
                  <tr key={a.id}>
                    <td>
                      <Link to={`/assignments/${a.id}`}>{a.title}</Link>
                    </td>
                    <td>
                      {formatDate(a.due_at)}
                      {overdue && !a.allow_late && <span className="meta"> · closed</span>}
                    </td>
                    <td className="num">{Number(a.max_marks)}</td>
                    {manager ? (
                      <>
                        <td className="num">{a.submission_count}</td>
                        <td className="num">{a.graded_count}</td>
                        <td className="actions">
                          <button className="link danger" onClick={() => remove(a.id, a.title)}>
                            Delete
                          </button>
                        </td>
                      </>
                    ) : (
                      <td>
                        {!a.my_submission && <span className="meta">Not submitted</span>}
                        {a.my_submission && !a.my_submission.graded && (
                          <span className="status active">Submitted</span>
                        )}
                        {a.my_submission?.graded && (
                          <span className="status completed">
                            {Number(a.my_submission.marks)} / {Number(a.max_marks)}
                          </span>
                        )}
                        {a.my_submission?.is_late && <span className="status late">Late</span>}
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function AssignmentForm({
  courseId,
  onDone,
  onCancel,
}: {
  courseId: number;
  onDone: () => void;
  onCancel: () => void;
}) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const due = form.get("due_at") as string;
    form.delete("due_at");
    if (due) form.append("due_at", new Date(due).toISOString());
    const file = form.get("attachment") as File | null;
    if (!file || file.size === 0) form.delete("attachment");
    form.set("allow_late", form.get("allow_late") ? "true" : "false");
    setError("");
    setBusy(true);
    try {
      await createAssignment(courseId, form);
      onDone();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel" onSubmit={onSubmit}>
      <h2>New assignment</h2>
      <div className="grid">
        <label>
          Title
          <input name="title" required maxLength={200} />
        </label>
        <label>
          Maximum marks
          <input name="max_marks" type="number" min="0" step="0.5" defaultValue="10" required />
        </label>
        <label>
          Due
          <input name="due_at" type="datetime-local" />
        </label>
        <label>
          Brief (optional file)
          <input name="attachment" type="file" />
        </label>
      </div>
      <label>
        Instructions
        <textarea name="description" rows={4} />
      </label>
      <label className="checkbox">
        <input type="checkbox" name="allow_late" />
        Accept late submissions
      </label>
      {error && <p className="error">{error}</p>}
      <div className="row">
        <button disabled={busy}>{busy ? "Posting…" : "Post assignment"}</button>
        <button type="button" className="secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
