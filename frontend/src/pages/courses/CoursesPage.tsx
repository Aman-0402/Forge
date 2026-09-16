import { useState } from "react";
import { Link } from "react-router-dom";
import { listCategories, listCourses } from "../../api/courses";
import { useAuth } from "../../auth/AuthContext";
import CourseCard from "../../components/CourseCard";
import Pager from "../../components/Pager";
import { useLoad } from "../../hooks/useLoad";

export default function CoursesPage() {
  const { user } = useAuth();
  const canCreate = user?.role === "admin" || user?.role === "faculty";
  const [filters, setFilters] = useState({ search: "", level: "", categories: "", status: "" });
  const [page, setPage] = useState(1);
  const courses = useLoad(() => listCourses({ ...filters, page }), [filters, page]);
  const categories = useLoad(listCategories, []);

  const set = (key: keyof typeof filters) => (e: { target: { value: string } }) => {
    setFilters({ ...filters, [key]: e.target.value });
    setPage(1);
  };

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">{canCreate ? "Teaching" : "Catalog"}</div>
          <h1>Courses</h1>
        </div>
        {canCreate && (
          <Link className="button" to="/courses/new">
            New course
          </Link>
        )}
      </div>

      <div className="toolbar">
        <input
          type="search"
          placeholder="Search by title, code or description"
          value={filters.search}
          onChange={set("search")}
          aria-label="Search courses"
        />
        <select value={filters.level} onChange={set("level")} aria-label="Level">
          <option value="">All levels</option>
          <option value="beginner">Beginner</option>
          <option value="intermediate">Intermediate</option>
          <option value="advanced">Advanced</option>
        </select>
        <select value={filters.categories} onChange={set("categories")} aria-label="Category">
          <option value="">All categories</option>
          {categories.data?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        {canCreate && (
          <select value={filters.status} onChange={set("status")} aria-label="Status">
            <option value="">Any status</option>
            <option value="draft">Draft</option>
            <option value="pending_approval">Awaiting approval</option>
            <option value="published">Published</option>
            <option value="archived">Archived</option>
          </select>
        )}
      </div>

      {courses.error && <p className="error">{courses.error}</p>}
      {courses.loading && !courses.data && <p className="hint">Loading courses…</p>}
      {courses.data?.results.length === 0 && (
        <div className="empty">
          <strong>No courses match</strong>
          {canCreate ? "Create a course to get started." : "Try a different search or filter."}
        </div>
      )}
      <div className="course-grid">
        {courses.data?.results.map((c) => (
          <CourseCard key={c.id} course={c} />
        ))}
      </div>
      {courses.data && courses.data.count > 20 && (
        <Pager page={page} count={courses.data.count} onPage={setPage} />
      )}
    </>
  );
}
