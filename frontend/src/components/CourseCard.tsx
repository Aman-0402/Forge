import { Link } from "react-router-dom";
import type { Course } from "../api/courses";
import TemperBar from "./TemperBar";

export const STATUS_LABEL: Record<string, string> = {
  draft: "Draft",
  pending_approval: "Awaiting approval",
  published: "Published",
  archived: "Archived",
  active: "Active",
  completed: "Completed",
  dropped: "Dropped",
};

export function StatusChip({ status }: { status: string }) {
  return <span className={`status ${status}`}>{STATUS_LABEL[status] ?? status}</span>;
}

export function plateCode(course: { code: string; title: string }) {
  if (course.code) return course.code;
  return course.title
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 3)
    .map((w) => w[0]?.toUpperCase())
    .join("");
}

export default function CourseCard({ course }: { course: Course }) {
  return (
    <Link to={`/courses/${course.id}`} className="course-card">
      <div className="course-plate">
        {course.thumbnail && <img src={course.thumbnail} alt="" />}
        <span className="plate-level">{course.level}</span>
        <span className="plate-code">{plateCode(course)}</span>
      </div>
      <div className="course-body">
        <h3>{course.title}</h3>
        <div className="course-meta">
          <span>{course.instructor_detail.name}</span>
          <span aria-hidden="true">·</span>
          <span>{course.lesson_count} lessons</span>
          {course.can_manage && (
            <>
              <span aria-hidden="true">·</span>
              <span>{course.enrollment_count} enrolled</span>
            </>
          )}
        </div>
        <div className="course-meta">
          {course.categories_detail.map((c) => (
            <span key={c.id} className="chip">
              {c.name}
            </span>
          ))}
          {course.can_manage && <StatusChip status={course.status} />}
        </div>
        <div className="course-foot">
          {course.is_enrolled && course.my_progress !== null ? (
            <TemperBar value={course.my_progress} label={`Progress in ${course.title}`} />
          ) : (
            course.enrollment_mode === "open" &&
            !course.can_manage && <span className="hint">Open for enrollment</span>
          )}
        </div>
      </div>
    </Link>
  );
}
