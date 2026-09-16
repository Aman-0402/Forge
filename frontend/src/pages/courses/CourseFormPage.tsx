import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { listDepartments, listUsers } from "../../api/admin";
import { errorMessage } from "../../api/client";
import {
  createCourse,
  getCourse,
  listCategories,
  updateCourse,
  type CourseInput,
  type EnrollmentMode,
  type Level,
} from "../../api/courses";
import { useAuth } from "../../auth/AuthContext";
import { useLoad } from "../../hooks/useLoad";

const EMPTY = {
  title: "",
  code: "",
  description: "",
  instructor: "",
  co_instructors: [] as string[],
  categories: [] as string[],
  department: "",
  level: "beginner" as Level,
  enrollment_mode: "manual" as EnrollmentMode,
  auto_enroll_batch: "",
  start_date: "",
  end_date: "",
};

export default function CourseFormPage() {
  const { id } = useParams();
  const editing = Boolean(id);
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const categories = useLoad(listCategories, []);
  const departments = useLoad(listDepartments, []);
  const faculty = useLoad(
    () =>
      isAdmin
        ? listUsers({ role: "faculty", is_active: true, page_size: 100 }).then((r) => r.results)
        : Promise.resolve([]),
    [isAdmin],
  );

  useEffect(() => {
    if (!id) return;
    getCourse(Number(id))
      .then((c) =>
        setForm({
          title: c.title,
          code: c.code,
          description: c.description,
          instructor: String(c.instructor),
          co_instructors: c.co_instructors.map(String),
          categories: c.categories.map(String),
          department: c.department ? String(c.department) : "",
          level: c.level,
          enrollment_mode: c.enrollment_mode,
          auto_enroll_batch: c.auto_enroll_batch,
          start_date: c.start_date ?? "",
          end_date: c.end_date ?? "",
        }),
      )
      .catch((err) => setError(errorMessage(err)));
  }, [id]);

  const set = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm({ ...form, [key]: e.target.value });

  const setMulti = (key: "categories" | "co_instructors") => (e: { target: HTMLSelectElement }) =>
    setForm({ ...form, [key]: Array.from(e.target.selectedOptions, (o) => o.value) });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    const body: CourseInput = {
      title: form.title,
      code: form.code,
      description: form.description,
      categories: form.categories.map(Number),
      co_instructors: form.co_instructors.map(Number),
      department: form.department ? Number(form.department) : null,
      level: form.level,
      enrollment_mode: form.enrollment_mode,
      auto_enroll_batch: form.auto_enroll_batch,
      start_date: form.start_date || null,
      end_date: form.end_date || null,
    };
    if (isAdmin && form.instructor) body.instructor = Number(form.instructor);
    try {
      const course = editing ? await updateCourse(Number(id), body) : await createCourse(body);
      navigate(`/courses/${course.id}`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const facultyOptions = (faculty.data ?? []).map((f) => (
    <option key={f.id} value={f.id}>
      {`${f.first_name} ${f.last_name}`.trim() || f.email} — {f.email}
    </option>
  ));

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">{editing ? "Edit course" : "New course"}</div>
          <h1>{editing ? form.title || "Course" : "Create a course"}</h1>
        </div>
        <Link className="button secondary" to={editing ? `/courses/${id}` : "/courses"}>
          Cancel
        </Link>
      </div>

      <form className="panel" onSubmit={onSubmit}>
        <h2>Details</h2>
        <div className="grid">
          <label>
            Title
            <input value={form.title} onChange={set("title")} required maxLength={200} />
          </label>
          <label>
            Course code
            <input value={form.code} onChange={set("code")} placeholder="e.g. CS101" maxLength={30} />
          </label>
          <label>
            Level
            <select value={form.level} onChange={set("level")}>
              <option value="beginner">Beginner</option>
              <option value="intermediate">Intermediate</option>
              <option value="advanced">Advanced</option>
            </select>
          </label>
        </div>
        <label>
          Description
          <textarea rows={5} value={form.description} onChange={set("description")} />
        </label>

        <h2>Teaching</h2>
        <div className="grid">
          {isAdmin && (
            <label>
              Instructor
              <select value={form.instructor} onChange={set("instructor")} required={!editing}>
                <option value="">Choose faculty…</option>
                {facultyOptions}
              </select>
            </label>
          )}
          {isAdmin && (
            <label>
              Co-instructors
              <select multiple size={4} value={form.co_instructors} onChange={setMulti("co_instructors")}>
                {facultyOptions}
              </select>
              <span className="hint">Hold Ctrl to select several.</span>
            </label>
          )}
          <label>
            Categories
            <select multiple size={4} value={form.categories} onChange={setMulti("categories")}>
              {categories.data?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
            <span className="hint">Hold Ctrl to select several.</span>
          </label>
          <label>
            Department
            <select value={form.department} onChange={set("department")}>
              <option value="">None</option>
              {departments.data?.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.code} — {d.name}
                </option>
              ))}
            </select>
          </label>
        </div>

        <h2>Enrollment and schedule</h2>
        <div className="grid">
          <label>
            Who can join
            <select value={form.enrollment_mode} onChange={set("enrollment_mode")}>
              <option value="manual">Only students I add</option>
              <option value="open">Any student can enroll</option>
              <option value="auto_department">Everyone in the department</option>
              <option value="auto_batch">Everyone in a batch</option>
            </select>
          </label>
          {form.enrollment_mode === "auto_batch" && (
            <label>
              Batch
              <input value={form.auto_enroll_batch} onChange={set("auto_enroll_batch")} required placeholder="e.g. 2026" />
            </label>
          )}
          <label>
            Starts
            <input type="date" value={form.start_date} onChange={set("start_date")} />
          </label>
          <label>
            Ends
            <input type="date" value={form.end_date} onChange={set("end_date")} />
          </label>
        </div>
        {form.enrollment_mode === "auto_department" && (
          <p className="hint">Students in the selected department are enrolled when the course is published.</p>
        )}

        {error && <p className="error">{error}</p>}
        <div className="row">
          <button disabled={busy}>{busy ? "Saving…" : editing ? "Save changes" : "Create course"}</button>
        </div>
      </form>
    </>
  );
}
