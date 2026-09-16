import { useState, type FormEvent } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { errorMessage } from "../../api/client";
import {
  addExamQuestions,
  deleteExam,
  downloadResultsCsv,
  examAction,
  examAttempts,
  examQuestions,
  examResults,
  extendExam,
  getExam,
  listBanks,
  listQuestions,
  myResults,
  removeExamQuestion,
  startExam,
  updateExamQuestion,
  type Exam,
} from "../../api/exams";
import Pager from "../../components/Pager";
import { useLoad } from "../../hooks/useLoad";
import { ATTEMPT_LABEL, PHASE_CLASS, PHASE_LABEL, TYPE_LABEL } from "../../utils/examLabels";
import { formatDate } from "../../utils/format";
import { confirmDialog, promptDialog, toast } from "../../utils/notify";

type Tab = "overview" | "questions" | "attempts" | "results";

export default function ExamPage() {
  const id = Number(useParams().id);
  const exam = useLoad(() => getExam(id), [id]);
  const e = exam.data;
  if (exam.error) return <p className="error">{exam.error}</p>;
  if (!e) return <p className="hint">Loading exam…</p>;
  return e.can_manage ? <StaffExam exam={e} reload={exam.reload} /> : <StudentExam exam={e} />;
}

function ExamHeader({ exam: e }: { exam: Exam }) {
  return (
    <>
      <div className="eyebrow">
        <Link to="/exams">Exams</Link>
        {e.course_title && ` / ${e.course_title}`}
      </div>
      <div className="page-head">
        <div>
          <div className="row">
            <span className={`status ${PHASE_CLASS[e.phase]}`}>{PHASE_LABEL[e.phase]}</span>
            {e.results_released_at && <span className="status completed">Results released</span>}
          </div>
          <h1>{e.title}</h1>
        </div>
      </div>
      <dl className="facts facts-wide panel">
        <dt>Opens</dt>
        <dd>{formatDate(e.starts_at)}</dd>
        <dt>Closes</dt>
        <dd>{formatDate(e.ends_at)}</dd>
        <dt>Time allowed</dt>
        <dd>{e.duration_minutes} minutes</dd>
        <dt>Questions</dt>
        <dd>
          {e.question_count} · {Number(e.total_marks)} marks
          {e.pass_marks && ` · pass at ${Number(e.pass_marks)}`}
        </dd>
        <dt>Attempts allowed</dt>
        <dd>{e.max_attempts}</dd>
      </dl>
    </>
  );
}

// ---------------------------------------------------------------- student

function StudentExam({ exam: e }: { exam: Exam }) {
  const navigate = useNavigate();
  const results = useLoad(() => myResults({ page_size: 50 }), []);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const mine = (results.data?.results ?? []).filter((r) => r.exam.id === e.id);

  async function begin() {
    setError("");
    setBusy(true);
    try {
      const attempt = await startExam(e.id);
      navigate(`/attempts/${attempt.id}/take`);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <>
      <ExamHeader exam={e} />
      {e.description && (
        <section className="panel">
          <h2>Instructions</h2>
          <p className="pre">{e.description}</p>
        </section>
      )}
      <section className="panel">
        <h2>Before you start</h2>
        <ul className="rules">
          <li>The timer starts when you press Start and keeps running if you close the page.</li>
          <li>Answers save as you go. You can come back with Resume while time remains.</li>
          <li>When time runs out your answers are submitted automatically.</li>
          {e.integrity_tracking && <li>Switching tabs or leaving full screen is recorded for your instructor.</li>}
        </ul>
        {e.my_attempts?.can_start ? (
          <button disabled={busy} onClick={begin}>
            {e.my_attempts.in_progress_id ? "Resume exam" : "Start exam"}
          </button>
        ) : (
          <p className="notice warn">
            {e.phase === "upcoming" && `This exam opens ${formatDate(e.starts_at)}.`}
            {(e.phase === "ended" || e.phase === "closed") && "This exam is closed."}
            {e.phase === "live" && `You have used all ${e.max_attempts} attempts.`}
          </p>
        )}
        {error && <p className="error">{error}</p>}
      </section>

      {mine.length > 0 && (
        <section className="panel">
          <h2>Your attempts</h2>
          <div className="table-wrap">
            <table>
              <tbody>
                {mine.map((r) => (
                  <tr key={r.attempt_id}>
                    <td>Attempt {r.attempt_number}</td>
                    <td>{formatDate(r.submitted_at)}</td>
                    <td>{ATTEMPT_LABEL[r.status]}</td>
                    <td>
                      {r.result_visible ? (
                        <Link to={`/attempts/${r.attempt_id}/result`}>
                          {Number(r.total_score)} marks · {Number(r.percentage)}%
                        </Link>
                      ) : (
                        <span className="meta">Result not released yet</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}

// ---------------------------------------------------------------- staff

function StaffExam({ exam: e, reload }: { exam: Exam; reload: () => void }) {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const tab = (params.get("tab") as Tab) || "overview";
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function run(action: () => Promise<unknown>, after = reload) {
    setError("");
    setBusy(true);
    try {
      await action();
      after();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const tabs: [Tab, string][] = [
    ["overview", "Overview"],
    ["questions", `Questions (${e.question_count})`],
    ["attempts", `Attempts (${e.attempt_count ?? 0})`],
    ["results", "Results"],
  ];

  return (
    <>
      <ExamHeader exam={e} />

      <section className="panel">
        <div className="panel-head">
          <h2>Publishing</h2>
          <Link className="button secondary small" to={`/exams/${e.id}/edit`}>
            Edit settings
          </Link>
        </div>
        <p className="hint">
          {e.status === "draft" && "Draft exams are invisible to students. Add questions, then schedule."}
          {e.phase === "upcoming" && `Scheduled. Students can start from ${formatDate(e.starts_at)}.`}
          {e.phase === "live" && "Open now. Students can start until the window closes."}
          {(e.phase === "ended" || e.status === "closed") &&
            (e.results_released_at
              ? `Closed. Results were released ${formatDate(e.results_released_at)}.`
              : "Closed. Grade any written answers, then release results.")}
        </p>
        <div className="row">
          {e.status === "draft" && (
            <button disabled={busy} onClick={() => run(() => examAction(e.id, "schedule"))}>
              Schedule exam
            </button>
          )}
          {e.status === "scheduled" && !e.attempt_count && (
            <button className="secondary" disabled={busy} onClick={() => run(() => examAction(e.id, "unschedule"))}>
              Back to draft
            </button>
          )}
          {e.status === "scheduled" && (
            <>
              <ExtendButton exam={e} onDone={reload} />
              <button
                className="secondary"
                disabled={busy}
                onClick={async () => {
                  const ok = await confirmDialog({
                    title: "Close the exam now?",
                    text: "Students still writing are submitted automatically.",
                  });
                  if (ok) run(() => examAction(e.id, "close"));
                }}
              >
                Close now
              </button>
            </>
          )}
          {e.status !== "draft" && !e.results_released_at && (
            <button disabled={busy} onClick={() => run(() => examAction(e.id, "release-results"))}>
              Release results
            </button>
          )}
          {e.status === "draft" && !e.attempt_count && (
            <button
              className="danger"
              disabled={busy}
              onClick={async () => {
                const ok = await confirmDialog({ title: "Delete this draft exam?", danger: true });
                if (ok) run(() => deleteExam(e.id), () => navigate("/exams"));
              }}
            >
              Delete draft
            </button>
          )}
        </div>
        {error && <p className="error">{error}</p>}
      </section>

      <div className="tabs" role="tablist">
        {tabs.map(([key, label]) => (
          <button
            key={key}
            role="tab"
            aria-selected={tab === key}
            onClick={() => setParams(key === "overview" ? {} : { tab: key }, { replace: true })}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <section className="panel">
          <h2>Instructions</h2>
          {e.description ? <p className="pre">{e.description}</p> : <p className="hint">No instructions.</p>}
          <ul className="rules">
            <li>{e.shuffle_questions ? "Questions are shuffled per student." : "Questions appear in a fixed order."}</li>
            <li>{e.integrity_tracking ? "Tab switches and full-screen exits are recorded." : "Integrity events are not recorded."}</li>
            <li>
              {e.show_result_immediately
                ? "Scores show right after submission when no written answers need grading."
                : "Students see scores only after you release results."}
            </li>
            <li>{e.reveal_answers ? "Correct answers are shown with results." : "Correct answers stay hidden."}</li>
          </ul>
        </section>
      )}
      {tab === "questions" && <QuestionsTab exam={e} onChange={reload} />}
      {tab === "attempts" && <AttemptsTab exam={e} />}
      {tab === "results" && <ResultsTab exam={e} />}
    </>
  );
}

function ExtendButton({ exam, onDone }: { exam: Exam; onDone: () => void }) {
  return (
    <button
      className="secondary"
      onClick={async () => {
        const minutes = await promptDialog({
          title: "Extend the closing time by how many minutes?",
          defaultValue: "30",
        });
        if (!minutes || Number(minutes) <= 0) return;
        const ends = new Date(new Date(exam.ends_at).getTime() + Number(minutes) * 60000);
        try {
          await extendExam(exam.id, ends.toISOString());
          onDone();
        } catch (err) {
          toast.error(errorMessage(err));
        }
      }}
    >
      Extend window
    </button>
  );
}

function QuestionsTab({ exam, onChange }: { exam: Exam; onChange: () => void }) {
  const rows = useLoad(() => examQuestions(exam.id), [exam.id]);
  const locked = Boolean(exam.attempt_count);
  const [error, setError] = useState("");

  async function run(action: () => Promise<unknown>) {
    setError("");
    try {
      await action();
      rows.reload();
      onChange();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <>
      {locked ? (
        <p className="notice warn">Students have attempted this exam, so its questions are locked.</p>
      ) : (
        <AddQuestions examId={exam.id} existing={(rows.data ?? []).map((r) => r.question.id)} onAdded={() => { rows.reload(); onChange(); }} />
      )}
      {(error || rows.error) && <p className="error">{error || rows.error}</p>}
      {rows.data?.length === 0 && (
        <div className="empty">
          <strong>No questions yet</strong>
          Pick questions from a bank above.
        </div>
      )}
      <ol className="cards numbered">
        {rows.data?.map((row) => (
          <li key={row.id} className="card-item">
            <div className="card-head">
              <div className="row">
                <span className="chip">{TYPE_LABEL[row.question.type]}</span>
                <span className="chip">{row.question.difficulty}</span>
                <span className="chip mono">{Number(row.marks)} marks</span>
              </div>
              {!locked && (
                <div className="row">
                  <button
                    className="link"
                    onClick={async () => {
                      const value = await promptDialog({
                        title: "Marks for this question in this exam",
                        placeholder: "blank = use the bank's marks",
                        defaultValue: row.marks_override ?? "",
                        allowBlank: true,
                      });
                      if (value === null) return;
                      run(() => updateExamQuestion(exam.id, row.id, { marks_override: value.trim() || null }));
                    }}
                  >
                    Set marks
                  </button>
                  <button className="link danger" onClick={() => run(() => removeExamQuestion(exam.id, row.id))}>
                    Remove
                  </button>
                </div>
              )}
            </div>
            <p className="pre">{row.question.text}</p>
            {row.question.options.length > 0 && (
              <ul className="option-list">
                {row.question.options.map((o) => (
                  <li key={o.id} className={o.is_correct ? "correct" : ""}>
                    {o.is_correct ? "✓ " : ""}
                    {o.text}
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ol>
    </>
  );
}

function AddQuestions({ examId, existing, onAdded }: { examId: number; existing: number[]; onAdded: () => void }) {
  const banks = useLoad(() => listBanks({ page_size: 100 }), []);
  const [bank, setBank] = useState("");
  const [mode, setMode] = useState<"pick" | "random">("pick");
  const [picked, setPicked] = useState<number[]>([]);
  const [count, setCount] = useState("5");
  const [difficulty, setDifficulty] = useState("");
  const [error, setError] = useState("");
  const questions = useLoad(
    () => (bank ? listQuestions(Number(bank), { is_active: true, page_size: 100 }) : Promise.resolve(null)),
    [bank],
  );

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      if (mode === "pick") await addExamQuestions(examId, { question_ids: picked });
      else await addExamQuestions(examId, { bank: Number(bank), count: Number(count), difficulty });
      setPicked([]);
      onAdded();
      questions.reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  const available = (questions.data?.results ?? []).filter((q) => !existing.includes(q.id));

  return (
    <form className="panel" onSubmit={onSubmit}>
      <h2>Add questions</h2>
      <div className="grid">
        <label>
          From bank
          <select value={bank} onChange={(e) => setBank(e.target.value)} required>
            <option value="">Choose a bank…</option>
            {banks.data?.results.map((b) => (
              <option key={b.id} value={b.id}>
                {b.title} ({b.question_count})
              </option>
            ))}
          </select>
        </label>
        <label>
          How
          <select value={mode} onChange={(e) => setMode(e.target.value as "pick" | "random")}>
            <option value="pick">Choose questions</option>
            <option value="random">Random selection</option>
          </select>
        </label>
        {mode === "random" && (
          <>
            <label>
              Number of questions
              <input type="number" min="1" value={count} onChange={(e) => setCount(e.target.value)} />
            </label>
            <label>
              Difficulty
              <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
                <option value="">Any</option>
                <option value="easy">Easy</option>
                <option value="medium">Medium</option>
                <option value="hard">Hard</option>
              </select>
            </label>
          </>
        )}
      </div>
      {mode === "pick" && bank && (
        <div className="pick-list">
          {available.length === 0 && <p className="hint">Every active question in this bank is already in the exam.</p>}
          {available.map((q) => (
            <label key={q.id} className="checkbox pick-item">
              <input
                type="checkbox"
                checked={picked.includes(q.id)}
                onChange={(ev) => setPicked(ev.target.checked ? [...picked, q.id] : picked.filter((x) => x !== q.id))}
              />
              <span className="chip">{TYPE_LABEL[q.type]}</span>
              <span className="grow">{q.text}</span>
              <span className="mono meta">{Number(q.marks)}</span>
            </label>
          ))}
        </div>
      )}
      {error && <p className="error">{error}</p>}
      <div className="row">
        <button disabled={!bank || (mode === "pick" && picked.length === 0)}>
          {mode === "pick" ? `Add ${picked.length || ""} selected` : "Add random questions"}
        </button>
      </div>
    </form>
  );
}

function AttemptsTab({ exam }: { exam: Exam }) {
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const list = useLoad(() => examAttempts(exam.id, { status, page }), [exam.id, status, page]);

  return (
    <>
      <div className="toolbar">
        <select
          value={status}
          onChange={(e) => {
            setStatus(e.target.value);
            setPage(1);
          }}
          aria-label="Attempt status"
        >
          <option value="">All attempts</option>
          <option value="grading">Awaiting grading</option>
          <option value="in_progress">In progress</option>
          <option value="graded">Graded</option>
        </select>
      </div>
      {list.error && <p className="error">{list.error}</p>}
      {list.data?.results.length === 0 && (
        <div className="empty">
          <strong>No attempts</strong>
          Attempts appear here once students start the exam.
        </div>
      )}
      {list.data && list.data.results.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Student</th>
                <th>Status</th>
                <th>Submitted</th>
                <th className="num">Score</th>
                <th className="num">Flags</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {list.data.results.map((a) => (
                <tr key={a.id}>
                  <td>
                    {a.student_detail.name}
                    <div className="meta">
                      {a.student_detail.email}
                      {a.attempt_number > 1 && ` · attempt ${a.attempt_number}`}
                    </div>
                  </td>
                  <td>
                    <span className={`status ${a.status === "graded" ? "completed" : a.status === "grading" ? "pending_approval" : "active"}`}>
                      {ATTEMPT_LABEL[a.status]}
                    </span>
                    {a.auto_submitted && <div className="meta">auto-submitted</div>}
                  </td>
                  <td>{formatDate(a.submitted_at)}</td>
                  <td className="num">
                    {a.status === "in_progress" ? "—" : `${Number(a.total_score)} (${Number(a.percentage)}%)`}
                  </td>
                  <td className="num">
                    {a.integrity_event_count > 0 ? <span className="status late">{a.integrity_event_count}</span> : "0"}
                  </td>
                  <td className="actions">
                    {a.status !== "in_progress" && (
                      <Link className="button small secondary" to={`/attempts/${a.id}/review`}>
                        {a.status === "grading" ? "Grade" : "Review"}
                      </Link>
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

function ResultsTab({ exam }: { exam: Exam }) {
  const summary = useLoad(() => examResults(exam.id), [exam.id]);
  const s = summary.data?.stats;

  return (
    <>
      {summary.error && <p className="error">{summary.error}</p>}
      {s && (
        <div className="stat-row">
          <Stat label="Graded" value={`${s.graded} / ${s.attempts}`} />
          <Stat label="Awaiting grading" value={String(s.awaiting_grading)} />
          <Stat label="Average" value={s.average ? `${Number(s.average)} / ${Number(s.total_marks)}` : "—"} />
          <Stat label="Highest" value={s.highest ? String(Number(s.highest)) : "—"} />
          <Stat label="Lowest" value={s.lowest ? String(Number(s.lowest)) : "—"} />
          <Stat label="Pass rate" value={s.pass_rate ? `${Number(s.pass_rate)}%` : "—"} />
        </div>
      )}
      <div className="panel-head">
        <h2>Graded attempts</h2>
        <button
          className="secondary small"
          disabled={!summary.data?.rows.length}
          onClick={() => downloadResultsCsv(exam.id, `${exam.title.replace(/\W+/g, "-").toLowerCase()}-results.csv`)}
        >
          Download CSV
        </button>
      </div>
      {summary.data && summary.data.rows.length === 0 && <p className="hint">No graded attempts yet.</p>}
      {summary.data && summary.data.rows.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Student</th>
                <th>Roll no.</th>
                <th className="num">Score</th>
                <th className="num">%</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {summary.data.rows.map((r, i) => (
                <tr key={r.attempt_id}>
                  <td className="mono">{i + 1}</td>
                  <td>
                    <Link to={`/attempts/${r.attempt_id}/review`}>{r.name}</Link>
                    <div className="meta">{r.email}</div>
                  </td>
                  <td className="mono">{r.roll_number ?? "—"}</td>
                  <td className="num">{Number(r.total_score)}</td>
                  <td className="num">{Number(r.percentage)}</td>
                  <td>
                    {r.passed === null ? "—" : r.passed ? <span className="status published">Pass</span> : <span className="status late">Fail</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}
