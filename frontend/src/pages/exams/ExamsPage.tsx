import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { errorMessage } from "../../api/client";
import { listExams, startExam, type Exam } from "../../api/exams";
import { useAuth } from "../../auth/AuthContext";
import Pager from "../../components/Pager";
import { useLoad } from "../../hooks/useLoad";
import { PHASE_CLASS, PHASE_LABEL } from "../../utils/examLabels";
import { formatDate } from "../../utils/format";

export default function ExamsPage() {
  const { user } = useAuth();
  const staff = user?.role === "admin" || user?.role === "faculty";
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const exams = useLoad(() => listExams({ status, page }), [status, page]);

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">Assessment</div>
          <h1>Exams</h1>
        </div>
        <div className="row">
          {staff && (
            <select
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1);
              }}
              aria-label="Status"
            >
              <option value="">Any status</option>
              <option value="draft">Draft</option>
              <option value="scheduled">Scheduled</option>
              <option value="closed">Closed</option>
            </select>
          )}
          {staff ? (
            <Link className="button" to="/exams/new">
              New exam
            </Link>
          ) : (
            <Link className="button secondary" to="/my-results">
              My results
            </Link>
          )}
        </div>
      </div>

      {exams.error && <p className="error">{exams.error}</p>}
      {exams.data?.results.length === 0 && (
        <div className="empty">
          <strong>No exams</strong>
          {staff ? "Create an exam, add questions from a bank, then schedule it." : "Exams you can sit appear here."}
        </div>
      )}
      {exams.data && exams.data.results.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Exam</th>
                <th>Window</th>
                <th className="num">Duration</th>
                <th className="num">Marks</th>
                <th>Status</th>
                <th>{staff ? "Attempts" : ""}</th>
              </tr>
            </thead>
            <tbody>
              {exams.data.results.map((e) => (
                <ExamRow key={e.id} exam={e} staff={staff} />
              ))}
            </tbody>
          </table>
        </div>
      )}
      {exams.data && <Pager page={page} count={exams.data.count} onPage={setPage} />}
    </>
  );
}

function ExamRow({ exam: e, staff }: { exam: Exam; staff: boolean }) {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function begin() {
    setError("");
    setBusy(true);
    try {
      const attempt = await startExam(e.id);
      navigate(`/attempts/${attempt.id}/take`);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  const mine = e.my_attempts;
  return (
    <tr>
      <td>
        <Link to={`/exams/${e.id}`}>{e.title}</Link>
        {e.course_title && <div className="meta">{e.course_title}</div>}
      </td>
      <td>
        {formatDate(e.starts_at)}
        <div className="meta">to {formatDate(e.ends_at)}</div>
      </td>
      <td className="num">{e.duration_minutes}m</td>
      <td className="num">{Number(e.total_marks)}</td>
      <td>
        <span className={`status ${PHASE_CLASS[e.phase]}`}>{PHASE_LABEL[e.phase]}</span>
      </td>
      <td className="actions">
        {staff && <span className="mono">{e.attempt_count ?? 0}</span>}
        {!staff && mine && (
          <>
            {mine.can_start && (
              <button className="small" disabled={busy} onClick={begin}>
                {mine.in_progress_id ? "Resume" : "Start exam"}
              </button>
            )}
            {!mine.can_start && (
              <span className="meta">
                {mine.used}/{mine.max} attempts used
              </span>
            )}
            {error && <div className="error">{error}</div>}
          </>
        )}
      </td>
    </tr>
  );
}
