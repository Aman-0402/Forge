import { Link } from "react-router-dom";
import type { Role } from "../api/auth";
import { listAnnouncements } from "../api/notifications";
import { listCourses, myEnrollments } from "../api/courses";
import { useAuth } from "../auth/AuthContext";
import CourseCard, { StatusChip, plateCode } from "../components/CourseCard";
import TemperBar from "../components/TemperBar";
import { useLoad } from "../hooks/useLoad";
import { formatDate } from "../utils/format";

export default function HomePage({ role }: { role: Role }) {
  const { user } = useAuth();
  const name = user?.first_name || user?.email;
  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">{new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" })}</div>
          <h1>Welcome, {name}</h1>
        </div>
      </div>
      {role === "student" && <StudentHome />}
      {role === "faculty" && <FacultyHome />}
      {role === "admin" && <AdminHome />}
      <RecentAnnouncements />
    </>
  );
}

function StudentHome() {
  const active = useLoad(() => myEnrollments({ status: "active" }), []);
  const rows = active.data?.results ?? [];
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Continue learning</h2>
        <Link to="/my-learning">All my courses</Link>
      </div>
      {active.error && <p className="error">{active.error}</p>}
      {active.data && rows.length === 0 && (
        <div className="empty">
          <strong>You are not enrolled in any course</strong>
          <Link to="/courses">Browse the catalog</Link> to find one.
        </div>
      )}
      {rows.length > 0 && (
        <div className="table-wrap">
          <table>
            <tbody>
              {rows.slice(0, 6).map((e) => (
                <tr key={e.id}>
                  <td>
                    <span className="chip code">{plateCode(e.course_detail)}</span>
                  </td>
                  <td>
                    <Link to={`/courses/${e.course}`}>{e.course_detail.title}</Link>
                    <div className="meta">{e.course_detail.instructor_name}</div>
                  </td>
                  <td>
                    <TemperBar value={e.progress_percent} label={`Progress in ${e.course_detail.title}`} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function FacultyHome() {
  const { user } = useAuth();
  const mine = useLoad(() => listCourses({ instructor: user?.id, page_size: 12 }), [user?.id]);
  return (
    <section>
      <div className="panel-head">
        <h2>Your courses</h2>
        <Link className="button small" to="/courses/new">
          New course
        </Link>
      </div>
      {mine.error && <p className="error">{mine.error}</p>}
      {mine.data?.results.length === 0 && (
        <div className="empty">
          <strong>No courses yet</strong>
          Create a course, add lessons, then submit it for approval.
        </div>
      )}
      <div className="course-grid">
        {mine.data?.results.map((c) => (
          <CourseCard key={c.id} course={c} />
        ))}
      </div>
    </section>
  );
}

function AdminHome() {
  const pending = useLoad(() => listCourses({ status: "pending_approval", page_size: 5 }), []);
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Courses awaiting approval</h2>
        <Link to="/admin/approvals">Review all</Link>
      </div>
      {pending.error && <p className="error">{pending.error}</p>}
      {pending.data?.results.length === 0 && <p className="hint">Nothing to review.</p>}
      {pending.data && pending.data.results.length > 0 && (
        <div className="table-wrap">
          <table>
            <tbody>
              {pending.data.results.map((c) => (
                <tr key={c.id}>
                  <td>
                    <Link to={`/courses/${c.id}?tab=manage`}>{c.title}</Link>
                    <div className="meta">{c.instructor_detail.name}</div>
                  </td>
                  <td>
                    <StatusChip status={c.status} />
                  </td>
                  <td className="meta">Submitted {formatDate(c.submitted_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function RecentAnnouncements() {
  const list = useLoad(() => listAnnouncements({ page_size: 4 }), []);
  if (!list.data || list.data.results.length === 0) return null;
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Announcements</h2>
        <Link to="/announcements">See all</Link>
      </div>
      <ul className="cards">
        {list.data.results.map((a) => (
          <li key={a.id} className="card-item">
            <div className="card-head">
              <strong>{a.title}</strong>
              <span className="meta">
                {a.course_title ?? a.department_code ?? a.audience} · {formatDate(a.published_at)}
              </span>
            </div>
            <p className="pre">{a.body.length > 220 ? `${a.body.slice(0, 220)}…` : a.body}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
