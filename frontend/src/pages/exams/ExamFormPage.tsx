import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { errorMessage } from "../../api/client";
import { listCourses } from "../../api/courses";
import { createExam, getExam, updateExam, type ExamInput } from "../../api/exams";
import { useLoad } from "../../hooks/useLoad";

/** datetime-local value in the browser's timezone. */
function toLocalInput(iso: string) {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function defaultWindow() {
  const start = new Date(Date.now() + 60 * 60 * 1000);
  start.setMinutes(0, 0, 0);
  const end = new Date(start.getTime() + 2 * 60 * 60 * 1000);
  return { starts_at: toLocalInput(start.toISOString()), ends_at: toLocalInput(end.toISOString()) };
}

export default function ExamFormPage() {
  const { id } = useParams();
  const editing = Boolean(id);
  const navigate = useNavigate();
  const courses = useLoad(
    () => listCourses({ page_size: 100 }).then((r) => r.results.filter((c) => c.can_manage)),
    [],
  );
  const [form, setForm] = useState({
    title: "",
    description: "",
    course: "",
    ...defaultWindow(),
    duration_minutes: "60",
    pass_marks: "",
    max_attempts: "1",
    shuffle_questions: true,
    shuffle_options: true,
    show_result_immediately: false,
    reveal_answers: false,
    integrity_tracking: true,
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!id) return;
    getExam(Number(id))
      .then((e) =>
        setForm({
          title: e.title,
          description: e.description,
          course: e.course ? String(e.course) : "",
          starts_at: toLocalInput(e.starts_at),
          ends_at: toLocalInput(e.ends_at),
          duration_minutes: String(e.duration_minutes),
          pass_marks: e.pass_marks ?? "",
          max_attempts: String(e.max_attempts),
          shuffle_questions: e.shuffle_questions,
          shuffle_options: e.shuffle_options,
          show_result_immediately: e.show_result_immediately,
          reveal_answers: e.reveal_answers,
          integrity_tracking: e.integrity_tracking,
        }),
      )
      .catch((err) => setError(errorMessage(err)));
  }, [id]);

  const set = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm({ ...form, [key]: e.target.value });
  const toggle = (key: keyof typeof form) => (e: { target: { checked: boolean } }) =>
    setForm({ ...form, [key]: e.target.checked });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    const body: ExamInput = {
      title: form.title,
      description: form.description,
      course: form.course ? Number(form.course) : null,
      starts_at: new Date(form.starts_at).toISOString(),
      ends_at: new Date(form.ends_at).toISOString(),
      duration_minutes: Number(form.duration_minutes),
      pass_marks: form.pass_marks || null,
      max_attempts: Number(form.max_attempts),
      shuffle_questions: form.shuffle_questions,
      shuffle_options: form.shuffle_options,
      show_result_immediately: form.show_result_immediately,
      reveal_answers: form.reveal_answers,
      integrity_tracking: form.integrity_tracking,
    };
    try {
      const exam = editing ? await updateExam(Number(id), body) : await createExam(body);
      navigate(`/exams/${exam.id}${editing ? "" : "?tab=questions"}`);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">{editing ? "Edit exam" : "New exam"}</div>
          <h1>{editing ? form.title || "Exam" : "Create an exam"}</h1>
        </div>
        <Link className="button secondary" to={editing ? `/exams/${id}` : "/exams"}>
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
            Course (optional)
            <select value={form.course} onChange={set("course")}>
              <option value="">Not tied to a course</option>
              {courses.data?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code ? `${c.code} — ` : ""}
                  {c.title}
                </option>
              ))}
            </select>
            <span className="hint">Course exams are open to students enrolled in the course.</span>
          </label>
        </div>
        <label>
          Instructions for students
          <textarea rows={3} value={form.description} onChange={set("description")} />
        </label>

        <h2>Timing</h2>
        <div className="grid">
          <label>
            Opens
            <input type="datetime-local" value={form.starts_at} onChange={set("starts_at")} required />
          </label>
          <label>
            Closes
            <input type="datetime-local" value={form.ends_at} onChange={set("ends_at")} required />
          </label>
          <label>
            Time allowed (minutes)
            <input type="number" min="1" value={form.duration_minutes} onChange={set("duration_minutes")} required />
            <span className="hint">A student who starts late still has to finish before the exam closes.</span>
          </label>
        </div>

        <h2>Scoring and rules</h2>
        <div className="grid">
          <label>
            Pass mark (optional)
            <input type="number" min="0" step="0.5" value={form.pass_marks} onChange={set("pass_marks")} />
          </label>
          <label>
            Attempts allowed
            <input type="number" min="1" max="10" value={form.max_attempts} onChange={set("max_attempts")} required />
          </label>
        </div>
        <div className="stack">
          <label className="checkbox">
            <input type="checkbox" checked={form.shuffle_questions} onChange={toggle("shuffle_questions")} />
            Shuffle question order for each student
          </label>
          <label className="checkbox">
            <input type="checkbox" checked={form.shuffle_options} onChange={toggle("shuffle_options")} />
            Shuffle answer options
          </label>
          <label className="checkbox">
            <input type="checkbox" checked={form.integrity_tracking} onChange={toggle("integrity_tracking")} />
            Record tab switches and leaving full screen
          </label>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={form.show_result_immediately}
              onChange={toggle("show_result_immediately")}
            />
            Show the score as soon as a fully auto-graded attempt is submitted
          </label>
          <label className="checkbox">
            <input type="checkbox" checked={form.reveal_answers} onChange={toggle("reveal_answers")} />
            Show correct answers and explanations with results
          </label>
        </div>

        {error && <p className="error">{error}</p>}
        <div className="row">
          <button disabled={busy}>{busy ? "Saving…" : editing ? "Save changes" : "Create and add questions"}</button>
        </div>
      </form>
    </>
  );
}
