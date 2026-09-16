import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { errorMessage } from "../../api/client";
import {
  createTestCase,
  deleteTestCase,
  getLeaderboard,
  getProblem,
  importTestCases,
  listProblemSubmissions,
  listTestCases,
  problemAction,
  rejudgeProblem,
  runCode,
  submitCode,
  type Problem,
  type RunResult,
  type SubmissionDetail,
} from "../../api/coding";
import { useAuth } from "../../auth/AuthContext";
import CodeEditor from "../../components/CodeEditor";
import Pager from "../../components/Pager";
import { useLoad } from "../../hooks/useLoad";
import { DIFFICULTY_LABEL, VERDICT_CLASS, VERDICT_LABEL } from "../../utils/codingLabels";
import { formatDate } from "../../utils/format";
import { confirmDialog, toast } from "../../utils/notify";

type Tab = "problem" | "submissions" | "leaderboard" | "tests";

const draftKey = (problemId: number, langId: number) => `forge.code.${problemId}.${langId}`;

function loadDraft(problemId: number, langId: number, fallback: string) {
  try {
    return localStorage.getItem(draftKey(problemId, langId)) ?? fallback;
  } catch {
    return fallback;
  }
}

export default function ProblemPage() {
  const id = Number(useParams().id);
  const problem = useLoad(() => getProblem(id), [id]);
  if (problem.error) return <p className="error">{problem.error}</p>;
  if (!problem.data) return <p className="hint">Loading problem…</p>;
  return <Workspace problem={problem.data} reload={problem.reload} />;
}

function Workspace({ problem: p, reload }: { problem: Problem; reload: () => void }) {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const tab = (params.get("tab") as Tab) || "problem";
  const isStudent = user?.role === "student";

  const [langId, setLangId] = useState<number>(p.languages[0]?.id ?? 0);
  const language = p.languages.find((l) => l.id === langId) ?? p.languages[0];
  const [code, setCode] = useState(() => (language ? loadDraft(p.id, language.id, language.default_template) : ""));
  const [useCustom, setUseCustom] = useState(false);
  const [stdin, setStdin] = useState(p.sample_cases[0]?.input ?? "");
  const [running, setRunning] = useState<"" | "run" | "submit">("");
  const [runResult, setRunResult] = useState<RunResult | null>(null);
  const [submission, setSubmission] = useState<SubmissionDetail | null>(null);
  const [error, setError] = useState("");
  const [historyTick, setHistoryTick] = useState(0);

  useEffect(() => {
    if (!language) return;
    try {
      localStorage.setItem(draftKey(p.id, language.id), code);
    } catch {
      /* storage unavailable: drafts are a convenience only */
    }
  }, [code, language, p.id]);

  function switchLanguage(nextId: number) {
    const next = p.languages.find((l) => l.id === nextId);
    if (!next) return;
    setLangId(nextId);
    setCode(loadDraft(p.id, next.id, next.default_template));
  }

  async function doRun() {
    if (!language) return;
    setError("");
    setRunning("run");
    setSubmission(null);
    try {
      setRunResult(
        await runCode(p.id, { language: language.id, source_code: code, ...(useCustom ? { stdin } : {}) }),
      );
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setRunning("");
    }
  }

  async function doSubmit() {
    if (!language) return;
    setError("");
    setRunning("submit");
    setRunResult(null);
    try {
      setSubmission(await submitCode(p.id, { language: language.id, source_code: code }));
      setHistoryTick((t) => t + 1);
      reload();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setRunning("");
    }
  }

  const tabs: [Tab, string][] = [
    ["problem", "Problem"],
    ["submissions", p.can_manage ? "Submissions" : "My submissions"],
    ["leaderboard", "Leaderboard"],
  ];
  if (p.can_manage) tabs.push(["tests", `Test cases (${p.test_case_count})`]);

  return (
    <div className="workspace">
      <section className="ws-left">
        <div className="eyebrow">
          <Link to="/problems">Problems</Link>
          {p.course_title && ` / ${p.course_title}`}
        </div>
        <div className="ws-title">
          <h1>{p.title}</h1>
          <div className="row">
            <span className={`difficulty ${p.difficulty}`}>{DIFFICULTY_LABEL[p.difficulty]}</span>
            <span className="chip mono">{p.max_score} pts</span>
            <span className="chip mono">{Number(p.time_limit_seconds)}s · {Math.round(p.memory_limit_kb / 1024)} MB</span>
            {p.my_status?.solved && <span className="status published">Solved</span>}
            {p.can_manage && <span className={`status ${p.status === "published" ? "published" : "draft"}`}>{p.status}</span>}
          </div>
        </div>

        {p.can_manage && <StaffBar problem={p} onChange={reload} />}

        <div className="tabs" role="tablist">
          {tabs.map(([key, label]) => (
            <button
              key={key}
              role="tab"
              aria-selected={tab === key}
              onClick={() => setParams(key === "problem" ? {} : { tab: key }, { replace: true })}
            >
              {label}
            </button>
          ))}
        </div>

        {tab === "problem" && <Statement problem={p} />}
        {tab === "submissions" && <Submissions problem={p} tick={historyTick} />}
        {tab === "leaderboard" && <Leaderboard problemId={p.id} tick={historyTick} />}
        {tab === "tests" && p.can_manage && <TestCases problem={p} onChange={reload} />}
      </section>

      <section className="ws-right">
        <div className="editor-bar">
          <select value={langId} onChange={(e) => switchLanguage(Number(e.target.value))} aria-label="Language">
            {p.languages.map((l) => (
              <option key={l.id} value={l.id}>
                {l.name} {l.version}
              </option>
            ))}
          </select>
          <button
            className="link"
            onClick={async () => {
              if (!language) return;
              if (await confirmDialog({ title: "Replace your code with the starter template?" })) {
                setCode(language.default_template);
              }
            }}
          >
            Reset
          </button>
          <span className="spacer" />
          <label className="checkbox">
            <input type="checkbox" checked={useCustom} onChange={(e) => setUseCustom(e.target.checked)} />
            Custom input
          </label>
          <button className="secondary" disabled={!!running || !language} onClick={doRun}>
            {running === "run" ? "Running…" : "Run"}
          </button>
          {isStudent && (
            <button disabled={!!running || !language || p.status !== "published"} onClick={doSubmit}>
              {running === "submit" ? "Judging…" : "Submit"}
            </button>
          )}
        </div>
        <div className="editor-frame">
          {language ? (
            <CodeEditor value={code} language={language.editor_mode} onChange={setCode} />
          ) : (
            <p className="hint">No languages are enabled for this problem.</p>
          )}
        </div>
        {useCustom && (
          <textarea
            className="stdin-box mono"
            rows={4}
            value={stdin}
            onChange={(e) => setStdin(e.target.value)}
            placeholder="Input passed to your program"
            aria-label="Custom input"
          />
        )}
        <div className="console" aria-live="polite">
          {error && <p className="error">{error}</p>}
          {!error && !runResult && !submission && (
            <p className="hint">
              Run checks your code against the sample cases. {isStudent ? "Submit judges it against every test case." : ""}
            </p>
          )}
          {runResult && <RunOutput result={runResult} />}
          {submission && <SubmissionOutput submission={submission} />}
        </div>
      </section>
    </div>
  );
}

function Statement({ problem: p }: { problem: Problem }) {
  return (
    <article className="statement">
      <p className="pre">{p.statement}</p>
      {p.input_format && (
        <>
          <h3>Input</h3>
          <p className="pre">{p.input_format}</p>
        </>
      )}
      {p.output_format && (
        <>
          <h3>Output</h3>
          <p className="pre">{p.output_format}</p>
        </>
      )}
      {p.constraints && (
        <>
          <h3>Constraints</h3>
          <p className="pre mono">{p.constraints}</p>
        </>
      )}
      {p.sample_cases.map((c, i) => (
        <div key={i} className="sample">
          <h3>Example {i + 1}</h3>
          <div className="sample-grid">
            <div>
              <div className="eyebrow">Input</div>
              <pre>{c.input}</pre>
            </div>
            <div>
              <div className="eyebrow">Output</div>
              <pre>{c.expected_output}</pre>
            </div>
          </div>
          {c.explanation && <p className="meta pre">{c.explanation}</p>}
        </div>
      ))}
      {p.tags.length > 0 && (
        <div className="row">
          {p.tags.map((t) => (
            <span key={t} className="chip">
              {t}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}

function Verdict({ verdict }: { verdict: keyof typeof VERDICT_LABEL | "" | null }) {
  if (!verdict) return null;
  return <span className={`status ${VERDICT_CLASS[verdict]}`}>{VERDICT_LABEL[verdict]}</span>;
}

function RunOutput({ result }: { result: RunResult }) {
  return (
    <div className="stack">
      {result.compile_output && <pre className="compile">{result.compile_output}</pre>}
      {result.results.map((r) => (
        <div key={r.index} className="case">
          <div className="row">
            <strong>{result.mode === "custom" ? "Your input" : `Sample ${r.index}`}</strong>
            {r.verdict && <Verdict verdict={r.verdict} />}
            <span className="spacer" />
            <span className="meta mono">
              {r.time_seconds != null && `${r.time_seconds}s`} {r.memory_kb != null && `· ${Math.round(r.memory_kb / 1024)} MB`}
            </span>
          </div>
          <div className="case-grid">
            <div>
              <div className="eyebrow">Output</div>
              <pre>{r.stdout || " "}</pre>
            </div>
            {r.expected_output !== null && (
              <div>
                <div className="eyebrow">Expected</div>
                <pre>{r.expected_output}</pre>
              </div>
            )}
          </div>
          {r.stderr && <pre className="compile">{r.stderr}</pre>}
        </div>
      ))}
    </div>
  );
}

function SubmissionOutput({ submission: s }: { submission: SubmissionDetail }) {
  return (
    <div className="stack">
      <div className="row">
        <Verdict verdict={s.verdict} />
        <strong className="mono">
          {s.score} pts · {s.passed_count}/{s.total_count} tests
        </strong>
        <span className="spacer" />
        <Link to={`/code-submissions/${s.id}`}>Details</Link>
      </div>
      {s.compile_output && <pre className="compile">{s.compile_output}</pre>}
      <div className="test-dots">
        {s.results.map((r) => (
          <span
            key={r.index}
            className={r.passed ? "dot pass" : "dot fail"}
            title={`Test ${r.index}: ${VERDICT_LABEL[r.verdict]}${r.hidden ? " (hidden)" : ""}`}
          >
            {r.index}
          </span>
        ))}
      </div>
    </div>
  );
}

function Submissions({ problem, tick }: { problem: Problem; tick: number }) {
  const [page, setPage] = useState(1);
  const list = useLoad(() => listProblemSubmissions(problem.id, { page }), [problem.id, page, tick]);
  return (
    <>
      {list.error && <p className="error">{list.error}</p>}
      {list.data?.results.length === 0 && <p className="hint">No submissions yet.</p>}
      {list.data && list.data.results.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {problem.can_manage && <th>Student</th>}
                <th>When</th>
                <th>Language</th>
                <th>Verdict</th>
                <th className="num">Score</th>
              </tr>
            </thead>
            <tbody>
              {list.data.results.map((s) => (
                <tr key={s.id}>
                  {problem.can_manage && <td>{s.student_name}</td>}
                  <td>
                    <Link to={`/code-submissions/${s.id}`}>{formatDate(s.submitted_at)}</Link>
                  </td>
                  <td>{s.language_name}</td>
                  <td>{s.verdict ? <Verdict verdict={s.verdict} /> : s.status}</td>
                  <td className="num">
                    {s.score} <span className="meta">({s.passed_count}/{s.total_count})</span>
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

function Leaderboard({ problemId, tick }: { problemId: number; tick: number }) {
  const board = useLoad(() => getLeaderboard(problemId), [problemId, tick]);
  const { user } = useAuth();
  if (board.error) return <p className="error">{board.error}</p>;
  if (board.data?.length === 0) return <p className="hint">Nobody has scored yet.</p>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th className="num">#</th>
            <th>Student</th>
            <th className="num">Best</th>
            <th className="num">Attempts</th>
            <th>Reached</th>
          </tr>
        </thead>
        <tbody>
          {board.data?.map((r) => (
            <tr key={r.student_id} className={r.student_id === user?.id ? "me" : ""}>
              <td className="num">{r.rank}</td>
              <td>{r.name}</td>
              <td className="num">{r.best_score}</td>
              <td className="num">{r.attempts}</td>
              <td>{formatDate(r.reached_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StaffBar({ problem: p, onChange }: { problem: Problem; onChange: () => void }) {
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function run(action: () => Promise<unknown>) {
    setError("");
    try {
      await action();
      onChange();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <div className="staff-bar">
      <div className="row">
        <button className="secondary small" onClick={() => navigate(`/problems/${p.id}/edit`)}>
          Edit
        </button>
        {p.status !== "published" && (
          <button className="small" onClick={() => run(() => problemAction(p.id, "publish"))}>
            Publish
          </button>
        )}
        {p.status === "published" && (
          <button className="secondary small" onClick={() => run(() => problemAction(p.id, "unpublish"))}>
            Unpublish
          </button>
        )}
        {p.status !== "archived" && (
          <button className="secondary small" onClick={() => run(() => problemAction(p.id, "archive"))}>
            Archive
          </button>
        )}
        <button
          className="secondary small"
          onClick={async () => {
            const ok = await confirmDialog({ title: "Re-run every submission against the current test cases?" });
            if (!ok) return;
            run(async () => {
              const r = await rejudgeProblem(p.id);
              toast.success(`Rejudged ${r.rejudged} submissions${r.failed ? `, ${r.failed} failed` : ""}.`);
            });
          }}
        >
          Rejudge all
        </button>
      </div>
      {error && <p className="error">{error}</p>}
    </div>
  );
}

function TestCases({ problem, onChange }: { problem: Problem; onChange: () => void }) {
  const cases = useLoad(() => listTestCases(problem.id), [problem.id]);
  const [form, setForm] = useState({ input: "", expected_output: "", is_sample: false, weight: "1", explanation: "" });
  const [json, setJson] = useState("");
  const [error, setError] = useState("");
  const sampleCount = useMemo(() => (cases.data ?? []).filter((c) => c.is_sample).length, [cases.data]);

  async function run(action: () => Promise<unknown>) {
    setError("");
    try {
      await action();
      cases.reload();
      onChange();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function add(e: FormEvent) {
    e.preventDefault();
    await run(() =>
      createTestCase(problem.id, {
        input: form.input,
        expected_output: form.expected_output,
        is_sample: form.is_sample,
        is_hidden: !form.is_sample,
        weight: Number(form.weight),
        explanation: form.explanation,
      }),
    );
    setForm({ input: "", expected_output: "", is_sample: false, weight: "1", explanation: "" });
  }

  return (
    <>
      {(error || cases.error) && <p className="error">{error || cases.error}</p>}
      <p className="hint">
        {cases.data?.length ?? 0} cases, {sampleCount} shown as examples. Hidden cases are never shown to students.
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Input</th>
              <th>Expected</th>
              <th>Shown</th>
              <th className="num">Weight</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {cases.data?.map((c, i) => (
              <tr key={c.id}>
                <td className="mono">{i + 1}</td>
                <td>
                  <pre className="cell">{c.input}</pre>
                </td>
                <td>
                  <pre className="cell">{c.expected_output}</pre>
                </td>
                <td>{c.is_sample ? <span className="chip">Example</span> : <span className="meta">Hidden</span>}</td>
                <td className="num">{c.weight}</td>
                <td className="actions">
                  <button className="link danger" onClick={() => run(() => deleteTestCase(c.id))}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <form className="panel" onSubmit={add}>
        <h2>Add a test case</h2>
        <div className="grid">
          <label>
            Input
            <textarea className="mono" rows={4} value={form.input} onChange={(e) => setForm({ ...form, input: e.target.value })} />
          </label>
          <label>
            Expected output
            <textarea
              className="mono"
              rows={4}
              value={form.expected_output}
              onChange={(e) => setForm({ ...form, expected_output: e.target.value })}
              required
            />
          </label>
        </div>
        <div className="row">
          <label className="checkbox">
            <input type="checkbox" checked={form.is_sample} onChange={(e) => setForm({ ...form, is_sample: e.target.checked })} />
            Show as an example in the statement
          </label>
          <label>
            Weight
            <input type="number" min="1" value={form.weight} onChange={(e) => setForm({ ...form, weight: e.target.value })} />
          </label>
        </div>
        {form.is_sample && (
          <label>
            Explanation (optional)
            <input value={form.explanation} onChange={(e) => setForm({ ...form, explanation: e.target.value })} />
          </label>
        )}
        <div className="row">
          <button>Add test case</button>
        </div>
      </form>

      <form
        className="panel"
        onSubmit={(e) => {
          e.preventDefault();
          let items: unknown;
          try {
            items = JSON.parse(json);
          } catch {
            setError("That is not valid JSON.");
            return;
          }
          if (!Array.isArray(items)) {
            setError("Paste a JSON array.");
            return;
          }
          run(() => importTestCases(problem.id, items as unknown[])).then(() => setJson(""));
        }}
      >
        <h2>Import test cases</h2>
        <p className="hint">
          JSON array of <code>{'{"input": "...", "expected_output": "...", "is_sample": false, "weight": 1}'}</code>. All or nothing.
        </p>
        <textarea className="mono" rows={6} value={json} onChange={(e) => setJson(e.target.value)} />
        <div className="row">
          <button className="secondary" disabled={!json.trim()}>
            Import
          </button>
        </div>
      </form>
    </>
  );
}
