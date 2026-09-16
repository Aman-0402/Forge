import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { errorMessage } from "../../api/client";
import {
  getAttempt,
  reportIntegrity,
  saveAnswer,
  submitAttempt,
  type AttemptQuestion,
  type LiveAttempt,
} from "../../api/exams";
import { TYPE_LABEL, formatDuration } from "../../utils/examLabels";

type Draft = { ids: number[]; text: string };
type SaveState = "idle" | "saving" | "saved" | "error";

export default function TakeExamPage() {
  const attemptId = Number(useParams().id);
  const [attempt, setAttempt] = useState<LiveAttempt | null>(null);
  const [loadError, setLoadError] = useState("");
  const [drafts, setDrafts] = useState<Record<number, Draft>>({});
  const [saveState, setSaveState] = useState<Record<number, SaveState>>({});
  const [current, setCurrent] = useState(0);
  const [remaining, setRemaining] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [finished, setFinished] = useState<LiveAttempt | null>(null);
  const [notice, setNotice] = useState("");

  const deadline = useRef(0);
  const textTimers = useRef<Record<number, number>>({});
  const submittedRef = useRef(false);

  // ---- load
  useEffect(() => {
    getAttempt(attemptId)
      .then((a) => {
        if (a.status !== "in_progress") {
          setFinished(a);
          return;
        }
        setAttempt(a);
        deadline.current = Date.now() + a.seconds_remaining * 1000;
        setRemaining(a.seconds_remaining);
        setDrafts(
          Object.fromEntries(
            a.questions.map((q) => [q.exam_question_id, { ids: q.answer.selected_option_ids, text: q.answer.text_answer }]),
          ),
        );
      })
      .catch((err) => setLoadError(errorMessage(err)));
  }, [attemptId]);

  // ---- save helpers
  const persist = useCallback(
    async (q: AttemptQuestion, draft: Draft) => {
      setSaveState((s) => ({ ...s, [q.exam_question_id]: "saving" }));
      try {
        const res = await saveAnswer(
          attemptId,
          q.exam_question_id,
          q.type === "subjective" ? { text_answer: draft.text } : { selected_option_ids: draft.ids },
        );
        deadline.current = Date.now() + res.seconds_remaining * 1000;
        setSaveState((s) => ({ ...s, [q.exam_question_id]: "saved" }));
      } catch (err) {
        setSaveState((s) => ({ ...s, [q.exam_question_id]: "error" }));
        const message = errorMessage(err);
        if (/submitted|time is up/i.test(message)) {
          submittedRef.current = true;
          setFinished(await getAttempt(attemptId));
        } else {
          setNotice(message);
        }
      }
    },
    [attemptId],
  );

  const flushTextSaves = useCallback(async () => {
    if (!attempt) return;
    const pending = Object.entries(textTimers.current);
    textTimers.current = {};
    await Promise.all(
      pending.map(([eqId, timer]) => {
        window.clearTimeout(timer);
        const q = attempt.questions.find((x) => x.exam_question_id === Number(eqId));
        return q ? persist(q, drafts[q.exam_question_id]) : Promise.resolve();
      }),
    );
  }, [attempt, drafts, persist]);

  const submit = useCallback(
    async (auto: boolean) => {
      if (submittedRef.current) return;
      submittedRef.current = true;
      setSubmitting(true);
      try {
        await flushTextSaves();
        setFinished(await submitAttempt(attemptId));
      } catch (err) {
        const refreshed = await getAttempt(attemptId).catch(() => null);
        if (refreshed && refreshed.status !== "in_progress") setFinished(refreshed);
        else {
          submittedRef.current = false;
          setNotice(`${auto ? "Automatic submission failed" : "Submission failed"}: ${errorMessage(err)}`);
        }
      } finally {
        setSubmitting(false);
      }
    },
    [attemptId, flushTextSaves],
  );

  // ---- timer
  useEffect(() => {
    if (!attempt || finished) return;
    const id = window.setInterval(() => {
      const left = Math.max(0, Math.round((deadline.current - Date.now()) / 1000));
      setRemaining(left);
      if (left === 0) submit(true);
    }, 1000);
    return () => window.clearInterval(id);
  }, [attempt, finished, submit]);

  // ---- integrity + leave warning
  useEffect(() => {
    if (!attempt || finished) return;
    const last: Record<string, number> = {};
    const send = (kind: string, metadata: Record<string, unknown> = {}) => {
      if (!attempt.exam.integrity_tracking) return;
      const now = Date.now();
      if (now - (last[kind] ?? 0) < 2000) return;
      last[kind] = now;
      reportIntegrity(attemptId, kind, metadata).catch(() => undefined);
    };
    const onVisibility = () => document.visibilityState === "hidden" && send("tab_switch");
    const onBlur = () => document.visibilityState === "visible" && send("window_blur");
    const onFullscreen = () => !document.fullscreenElement && send("fullscreen_exit");
    const onCopy = () => send("copy");
    const onPaste = () => send("paste");
    const onLeave = (e: BeforeUnloadEvent) => {
      e.preventDefault();
    };
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("blur", onBlur);
    document.addEventListener("fullscreenchange", onFullscreen);
    document.addEventListener("copy", onCopy);
    document.addEventListener("paste", onPaste);
    window.addEventListener("beforeunload", onLeave);
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("blur", onBlur);
      document.removeEventListener("fullscreenchange", onFullscreen);
      document.removeEventListener("copy", onCopy);
      document.removeEventListener("paste", onPaste);
      window.removeEventListener("beforeunload", onLeave);
    };
  }, [attempt, finished, attemptId]);

  // ---- render
  if (loadError) return <p className="error">{loadError}</p>;
  if (finished) return <Finished attempt={finished} />;
  if (!attempt) return <p className="hint">Loading your exam…</p>;

  const questions = attempt.questions;
  const q = questions[current];
  const draft = drafts[q.exam_question_id] ?? { ids: [], text: "" };
  const answeredCount = questions.filter((x) => {
    const d = drafts[x.exam_question_id];
    return d && (d.ids.length > 0 || d.text.trim());
  }).length;
  const urgency = remaining <= 60 ? "danger" : remaining <= 300 ? "warn" : "";

  function choose(optionId: number) {
    const ids =
      q.type === "mcq_multi"
        ? draft.ids.includes(optionId)
          ? draft.ids.filter((x) => x !== optionId)
          : [...draft.ids, optionId]
        : [optionId];
    const next = { ...draft, ids };
    setDrafts({ ...drafts, [q.exam_question_id]: next });
    persist(q, next);
  }

  function write(text: string) {
    const next = { ...draft, text };
    setDrafts({ ...drafts, [q.exam_question_id]: next });
    setSaveState((s) => ({ ...s, [q.exam_question_id]: "idle" }));
    window.clearTimeout(textTimers.current[q.exam_question_id]);
    textTimers.current[q.exam_question_id] = window.setTimeout(() => {
      delete textTimers.current[q.exam_question_id];
      persist(q, next);
    }, 900);
  }

  async function go(index: number) {
    await flushTextSaves();
    setCurrent(index);
  }

  const state = saveState[q.exam_question_id] ?? "idle";

  return (
    <div className="exam-shell">
      <header className="exam-bar">
        <div>
          <div className="eyebrow">Attempt {attempt.attempt_number}</div>
          <strong>{attempt.exam.title}</strong>
        </div>
        <span className="spacer" />
        <span className="meta">
          {answeredCount}/{questions.length} answered
        </span>
        {document.fullscreenEnabled && !document.fullscreenElement && (
          <button className="secondary small" onClick={() => document.documentElement.requestFullscreen().catch(() => undefined)}>
            Full screen
          </button>
        )}
        <div className={`timer ${urgency}`} role="timer" aria-live={remaining <= 60 ? "assertive" : "off"}>
          {formatDuration(remaining)}
        </div>
      </header>

      {notice && (
        <p className="notice danger" role="alert">
          {notice}
        </p>
      )}

      <div className="exam-body">
        <article className="question-panel">
          <div className="question-head">
            <span className="eyebrow">
              Question {current + 1} of {questions.length}
            </span>
            <span className="row">
              <span className="chip">{TYPE_LABEL[q.type]}</span>
              <span className="chip mono">
                {Number(q.marks)} marks{Number(q.negative_marks) > 0 && ` · −${Number(q.negative_marks)} if wrong`}
              </span>
            </span>
          </div>
          <p className="question-text">{q.text}</p>

          {q.type === "subjective" ? (
            <textarea
              className="answer-text"
              rows={10}
              value={draft.text}
              onChange={(e) => write(e.target.value)}
              onBlur={() => flushTextSaves()}
              placeholder="Write your answer"
              aria-label="Your answer"
            />
          ) : (
            <div className="choices" role={q.type === "mcq_multi" ? "group" : "radiogroup"}>
              {q.options.map((o, i) => {
                const selected = draft.ids.includes(o.id);
                return (
                  <label key={o.id} className={selected ? "choice selected" : "choice"}>
                    <input
                      type={q.type === "mcq_multi" ? "checkbox" : "radio"}
                      name={`q-${q.exam_question_id}`}
                      checked={selected}
                      onChange={() => choose(o.id)}
                    />
                    <span className="choice-key">{String.fromCharCode(65 + i)}</span>
                    <span>{o.text}</span>
                  </label>
                );
              })}
              {q.type === "mcq_multi" && <p className="hint">Select every correct answer.</p>}
            </div>
          )}

          <div className="question-foot">
            <span className={`save-state ${state}`}>
              {state === "saving" && "Saving…"}
              {state === "saved" && "Saved"}
              {state === "error" && "Not saved — check your connection"}
            </span>
            <span className="spacer" />
            <button className="secondary" disabled={current === 0} onClick={() => go(current - 1)}>
              Previous
            </button>
            {current < questions.length - 1 ? (
              <button onClick={() => go(current + 1)}>Next</button>
            ) : (
              <button
                disabled={submitting}
                onClick={() =>
                  window.confirm(
                    `Submit now? ${questions.length - answeredCount} questions are unanswered. You cannot change answers after submitting.`,
                  ) && submit(false)
                }
              >
                {submitting ? "Submitting…" : "Submit exam"}
              </button>
            )}
          </div>
        </article>

        <aside className="palette" aria-label="Question navigator">
          <div className="palette-grid">
            {questions.map((x, i) => {
              const d = drafts[x.exam_question_id];
              const done = d && (d.ids.length > 0 || d.text.trim());
              return (
                <button
                  key={x.exam_question_id}
                  className={["palette-item", done ? "done" : "", i === current ? "current" : ""].join(" ")}
                  onClick={() => go(i)}
                  aria-current={i === current}
                  aria-label={`Question ${i + 1}${done ? ", answered" : ""}`}
                >
                  {i + 1}
                </button>
              );
            })}
          </div>
          <button
            className="danger submit-all"
            disabled={submitting}
            onClick={() =>
              window.confirm(`Submit now? ${questions.length - answeredCount} questions are unanswered.`) && submit(false)
            }
          >
            Submit exam
          </button>
        </aside>
      </div>
    </div>
  );
}

function Finished({ attempt }: { attempt: LiveAttempt }) {
  return (
    <section className="panel narrow finished">
      <div className="eyebrow">{attempt.exam.title}</div>
      <h1>Answers submitted</h1>
      {attempt.auto_submitted && <p className="notice warn">Time ran out, so your answers were submitted automatically.</p>}
      <p>
        {attempt.status === "grading"
          ? "Some answers need grading by your instructor. You will be notified when results are released."
          : "Your attempt has been scored. You can see the result once your instructor releases it."}
      </p>
      <div className="row">
        <Link className="button" to={`/attempts/${attempt.id}/result`}>
          View result
        </Link>
        <Link className="button secondary" to={`/exams/${attempt.exam.id}`}>
          Back to exam
        </Link>
      </div>
    </section>
  );
}
