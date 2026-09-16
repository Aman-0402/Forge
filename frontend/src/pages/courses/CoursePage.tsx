import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { errorMessage } from "../../api/client";
import { dropCourse, enroll, getCourse, getTree, type Course } from "../../api/courses";
import { useAuth } from "../../auth/AuthContext";
import { StatusChip, plateCode } from "../../components/CourseCard";
import TemperBar from "../../components/TemperBar";
import { useLoad } from "../../hooks/useLoad";
import { formatDate } from "../../utils/format";
import { confirmDialog } from "../../utils/notify";
import AssignmentsTab from "./AssignmentsTab";
import LearnTab from "./LearnTab";
import ManageTab from "./ManageTab";
import StudentsTab from "./StudentsTab";

type Tab = "learn" | "assignments" | "students" | "manage";

const MODE_LABEL: Record<Course["enrollment_mode"], string> = {
  manual: "Added by instructor",
  open: "Open enrollment",
  auto_department: "Automatic (department)",
  auto_batch: "Automatic (batch)",
};

export default function CoursePage() {
  const courseId = Number(useParams().id);
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const course = useLoad(() => getCourse(courseId), [courseId]);
  const tree = useLoad(() => getTree(courseId), [courseId]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const c = course.data;
  if (course.error) return <p className="error">{course.error}</p>;
  if (!c) return <p className="hint">Loading course…</p>;

  const manager = c.can_manage;
  const hasAccess = manager || c.is_enrolled;
  const tabs: [Tab, string][] = [["learn", "Content"]];
  if (hasAccess) tabs.push(["assignments", "Assignments"]);
  if (manager) tabs.push(["students", "Students"], ["manage", "Manage"]);
  const requested = params.get("tab") as Tab | null;
  const tab = tabs.some(([t]) => t === requested) ? (requested as Tab) : "learn";

  const reload = () => {
    course.reload();
    tree.reload();
  };

  async function run(action: () => Promise<unknown>) {
    setError("");
    setBusy(true);
    try {
      await action();
      reload();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const progress = tree.data?.progress_percent ?? c.my_progress;

  return (
    <>
      <div className="eyebrow">
        <Link to="/courses">Courses</Link> / {plateCode(c)}
      </div>
      <section className="course-hero">
        <div>
          <div className="row">
            <span className="chip code">{plateCode(c)}</span>
            <span className="chip">{c.level}</span>
            {manager && <StatusChip status={c.status} />}
            {c.categories_detail.map((cat) => (
              <span key={cat.id} className="chip">
                {cat.name}
              </span>
            ))}
          </div>
          <h1>{c.title}</h1>
          {c.description && <p className="lede pre">{c.description}</p>}
          {manager && c.status === "draft" && c.rejection_reason && (
            <p className="notice warn">Changes requested by admin: {c.rejection_reason}</p>
          )}
        </div>

        <aside className="hero-side">
          {c.is_enrolled && progress !== null && (
            <>
              <div className="eyebrow">Your progress</div>
              <TemperBar value={progress} large label="Course progress" />
            </>
          )}
          <dl className="facts">
            <dt>Instructor</dt>
            <dd>{c.instructor_detail.name}</dd>
            {c.co_instructors_detail.length > 0 && (
              <>
                <dt>With</dt>
                <dd>{c.co_instructors_detail.map((u) => u.name).join(", ")}</dd>
              </>
            )}
            <dt>Lessons</dt>
            <dd>{c.lesson_count}</dd>
            {manager && (
              <>
                <dt>Enrolled</dt>
                <dd>{c.enrollment_count}</dd>
              </>
            )}
            <dt>Joining</dt>
            <dd>{MODE_LABEL[c.enrollment_mode]}</dd>
            {(c.start_date || c.end_date) && (
              <>
                <dt>Runs</dt>
                <dd>
                  {c.start_date ?? "—"} to {c.end_date ?? "—"}
                </dd>
              </>
            )}
            {manager && c.approved_at && (
              <>
                <dt>Published</dt>
                <dd>{formatDate(c.approved_at)}</dd>
              </>
            )}
          </dl>

          {user?.role === "student" && !c.is_enrolled && c.enrollment_mode === "open" && c.status === "published" && (
            <button disabled={busy} onClick={() => run(() => enroll(c.id))}>
              Enroll in this course
            </button>
          )}
          {user?.role === "student" && !c.is_enrolled && c.enrollment_mode !== "open" && (
            <p className="hint">Your instructor or an administrator adds students to this course.</p>
          )}
          {user?.role === "student" && c.is_enrolled && c.enrollment_mode === "open" && (
            <button
              className="secondary small"
              disabled={busy}
              onClick={async () => {
                const ok = await confirmDialog({
                  title: "Leave this course?",
                  text: "Your progress is kept.",
                });
                if (ok) run(() => dropCourse(c.id));
              }}
            >
              Leave course
            </button>
          )}
          {error && <p className="error">{error}</p>}
        </aside>
      </section>

      <div className="tabs" role="tablist">
        {tabs.map(([key, label]) => (
          <button
            key={key}
            role="tab"
            aria-selected={tab === key}
            onClick={() => setParams(key === "learn" ? {} : { tab: key }, { replace: true })}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "learn" && (
        <LearnTab tree={tree.data} error={tree.error} onProgress={reload} canTrack={c.is_enrolled} />
      )}
      {tab === "assignments" && <AssignmentsTab course={c} />}
      {tab === "students" && <StudentsTab course={c} />}
      {tab === "manage" && <ManageTab course={c} tree={tree.data} onChange={reload} />}
    </>
  );
}
