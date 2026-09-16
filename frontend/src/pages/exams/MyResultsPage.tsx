import { useState } from "react";
import { Link } from "react-router-dom";
import { myResults } from "../../api/exams";
import Pager from "../../components/Pager";
import TemperBar from "../../components/TemperBar";
import { useLoad } from "../../hooks/useLoad";
import { ATTEMPT_LABEL } from "../../utils/examLabels";
import { formatDate } from "../../utils/format";

export default function MyResultsPage() {
  const [page, setPage] = useState(1);
  const list = useLoad(() => myResults({ page }), [page]);

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">Student</div>
          <h1>My results</h1>
        </div>
        <Link className="button secondary" to="/exams">
          Exams
        </Link>
      </div>
      {list.error && <p className="error">{list.error}</p>}
      {list.data?.results.length === 0 && (
        <div className="empty">
          <strong>No submitted exams yet</strong>
          Results appear here after you submit an exam.
        </div>
      )}
      {list.data && list.data.results.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Exam</th>
                <th>Submitted</th>
                <th>Status</th>
                <th>Score</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {list.data.results.map((r) => (
                <tr key={r.attempt_id}>
                  <td>
                    <Link to={`/exams/${r.exam.id}`}>{r.exam.title}</Link>
                    {r.attempt_number > 1 && <div className="meta">Attempt {r.attempt_number}</div>}
                  </td>
                  <td>{formatDate(r.submitted_at)}</td>
                  <td>{ATTEMPT_LABEL[r.status]}</td>
                  <td>
                    {r.result_visible ? (
                      <TemperBar value={Number(r.percentage)} label={`Score in ${r.exam.title}`} />
                    ) : (
                      <span className="meta">Not released</span>
                    )}
                  </td>
                  <td>
                    {r.result_visible ? (
                      <Link to={`/attempts/${r.attempt_id}/result`}>
                        {Number(r.total_score)} marks
                        {r.passed === true && " · passed"}
                        {r.passed === false && " · not passed"}
                      </Link>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {list.data && <Pager page={page} count={list.data.count} onPage={setPage} />}
    </>
  );
}
