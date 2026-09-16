import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { errorMessage } from "../../api/client";
import { createProblem, getProblem, listLanguages, updateProblem, type ProblemInput } from "../../api/coding";
import { listCourses } from "../../api/courses";
import { useLoad } from "../../hooks/useLoad";

export default function ProblemFormPage() {
  const { id } = useParams();
  const editing = Boolean(id);
  const navigate = useNavigate();
  const languages = useLoad(listLanguages, []);
  const courses = useLoad(
    () => listCourses({ page_size: 100 }).then((r) => r.results.filter((c) => c.can_manage)),
    [],
  );
  const [form, setForm] = useState({
    title: "",
    statement: "",
    input_format: "",
    output_format: "",
    constraints: "",
    difficulty: "easy",
    tags: "",
    time_limit_seconds: "2",
    memory_limit_kb: "128000",
    max_score: "100",
    allow_partial: true,
    course: "",
    allowed_languages: [] as number[],
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!id) return;
    getProblem(Number(id))
      .then((p) =>
        setForm({
          title: p.title,
          statement: p.statement,
          input_format: p.input_format,
          output_format: p.output_format,
          constraints: p.constraints,
          difficulty: p.difficulty,
          tags: p.tags.join(", "),
          time_limit_seconds: String(Number(p.time_limit_seconds)),
          memory_limit_kb: String(p.memory_limit_kb),
          max_score: String(p.max_score),
          allow_partial: p.allow_partial,
          course: p.course ? String(p.course) : "",
          allowed_languages: p.allowed_languages,
        }),
      )
      .catch((err) => setError(errorMessage(err)));
  }, [id]);

  const set = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm({ ...form, [key]: e.target.value });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    const body: ProblemInput = {
      title: form.title,
      statement: form.statement,
      input_format: form.input_format,
      output_format: form.output_format,
      constraints: form.constraints,
      difficulty: form.difficulty as ProblemInput["difficulty"],
      tags: form.tags.split(",").map((t) => t.trim()).filter(Boolean),
      time_limit_seconds: form.time_limit_seconds,
      memory_limit_kb: Number(form.memory_limit_kb),
      max_score: Number(form.max_score),
      allow_partial: form.allow_partial,
      course: form.course ? Number(form.course) : null,
      allowed_languages: form.allowed_languages,
    };
    try {
      const problem = editing ? await updateProblem(Number(id), body) : await createProblem(body);
      navigate(`/problems/${problem.id}${editing ? "" : "?tab=tests"}`);
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
          <div className="eyebrow">{editing ? "Edit problem" : "New problem"}</div>
          <h1>{editing ? form.title || "Problem" : "Write a problem"}</h1>
        </div>
        <Link className="button secondary" to={editing ? `/problems/${id}` : "/problems"}>
          Cancel
        </Link>
      </div>

      <form className="panel" onSubmit={onSubmit}>
        <div className="grid">
          <label>
            Title
            <input value={form.title} onChange={set("title")} required maxLength={200} />
          </label>
          <label>
            Difficulty
            <select value={form.difficulty} onChange={set("difficulty")}>
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </label>
          <label>
            Course (optional)
            <select value={form.course} onChange={set("course")}>
              <option value="">Open to all students</option>
              {courses.data?.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code ? `${c.code} — ` : ""}
                  {c.title}
                </option>
              ))}
            </select>
          </label>
          <label>
            Tags (comma separated)
            <input value={form.tags} onChange={set("tags")} placeholder="arrays, two pointers" />
          </label>
        </div>
        <label>
          Statement
          <textarea rows={6} value={form.statement} onChange={set("statement")} required />
        </label>
        <div className="grid">
          <label>
            Input format
            <textarea rows={3} value={form.input_format} onChange={set("input_format")} />
          </label>
          <label>
            Output format
            <textarea rows={3} value={form.output_format} onChange={set("output_format")} />
          </label>
          <label>
            Constraints
            <textarea rows={3} value={form.constraints} onChange={set("constraints")} placeholder="1 ≤ n ≤ 10^5" />
          </label>
        </div>

        <h2>Judging</h2>
        <div className="grid">
          <label>
            Time limit (seconds)
            <input type="number" min="0.1" max="15" step="0.1" value={form.time_limit_seconds} onChange={set("time_limit_seconds")} />
          </label>
          <label>
            Memory limit (KB)
            <input type="number" min="2048" max="512000" step="1024" value={form.memory_limit_kb} onChange={set("memory_limit_kb")} />
          </label>
          <label>
            Points
            <input type="number" min="1" value={form.max_score} onChange={set("max_score")} />
          </label>
        </div>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={form.allow_partial}
            onChange={(e) => setForm({ ...form, allow_partial: e.target.checked })}
          />
          Give partial points when some test cases pass
        </label>
        <fieldset className="options-edit">
          <legend>Languages (none selected = all enabled languages)</legend>
          <div className="row">
            {languages.data?.map((lang) => (
              <label key={lang.id} className="checkbox">
                <input
                  type="checkbox"
                  checked={form.allowed_languages.includes(lang.id)}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      allowed_languages: e.target.checked
                        ? [...form.allowed_languages, lang.id]
                        : form.allowed_languages.filter((x) => x !== lang.id),
                    })
                  }
                />
                {lang.name}
              </label>
            ))}
          </div>
        </fieldset>

        {error && <p className="error">{error}</p>}
        <div className="row">
          <button disabled={busy}>{busy ? "Saving…" : editing ? "Save changes" : "Create and add test cases"}</button>
        </div>
      </form>
    </>
  );
}
