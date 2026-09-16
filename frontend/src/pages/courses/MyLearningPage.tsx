import { useState } from "react";
import { Link } from "react-router-dom";
import { myEnrollments } from "../../api/courses";
import { StatusChip, plateCode } from "../../components/CourseCard";
import Pager from "../../components/Pager";
import TemperBar from "../../components/TemperBar";
import { useLoad } from "../../hooks/useLoad";
import { formatDate } from "../../utils/format";

export default function MyLearningPage() {
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const list = useLoad(() => myEnrollments({ status, page }), [status, page]);

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">Student</div>
          <h1>My learning</h1>
        </div>
        <select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
          aria-label="Filter by status"
        >
          <option value="">All courses</option>
          <option value="active">In progress</option>
          <option value="completed">Completed</option>
          <option value="dropped">Left</option>
        </select>
      </div>
      {list.error && <p className="error">{list.error}</p>}
      {list.data?.results.length === 0 && (
        <div className="empty">
          <strong>Nothing here yet</strong>
          <Link to="/courses">Browse the catalog</Link> to enroll in a course.
        </div>
      )}
      {list.data && list.data.results.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Course</th>
                <th>Progress</th>
                <th>Status</th>
                <th>Enrolled</th>
              </tr>
            </thead>
            <tbody>
              {list.data.results.map((e) => (
                <tr key={e.id} className={e.status === "dropped" ? "muted" : ""}>
                  <td>
                    <div className="row">
                      <span className="chip code">{plateCode(e.course_detail)}</span>
                      <div>
                        <Link to={`/courses/${e.course}`}>{e.course_detail.title}</Link>
                        <div className="meta">{e.course_detail.instructor_name}</div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <TemperBar value={e.progress_percent} label={`Progress in ${e.course_detail.title}`} />
                  </td>
                  <td>
                    <StatusChip status={e.status} />
                  </td>
                  <td>{formatDate(e.enrolled_at)}</td>
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
