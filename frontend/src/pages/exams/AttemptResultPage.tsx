import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { errorMessage } from "../../api/client";
import { attemptResult, gradeAnswer, reviewAttempt, type ResultAnswer } from "../../api/exams";
import TemperBar from "../../components/TemperBar";
import { useLoad } from "../../hooks/useLoad";
import { ATTEMPT_LABEL, TYPE_LABEL } from "../../utils/examLabels";
import { formatDate } from "../../utils/format";

/** Student scorecard (`/attempts/:id/result`) and staff review + grading (`/attempts/:id/review`). */
export default function AttemptResultPage({ review = false }: { review?: boolean }) {
  const id = Number(useParams().id);
  const data = useLoad(() => (review ? reviewAttempt(id) : attemptResult(id)), [id, review]);
  const r = data.data;

  if (data.error) {
    return (
      <section className="panel narrow">
        <h1>Result not available</h1>
        <p>{data.error}</p>
        <Link className="button secondary" to="/my-results">
          My results
        </Link>
      </section>
    );
  }
  if (!r) return <p className="hint">Loading…</p>;

  const pct = Number(r.percentage);
  return (
    <>
      <div className="eyebrow">
        <Link to={review ? `/exams/${r.exam.id}?tab=attempts` : `/exams/${r.exam.id}`}>{r.exam.title}</Link>
        {" / "}
        {review ? "Review attempt" : "Result"}
      </div>

      <section className="scorecard">
        <div>
          {r.student && <div className="eyebrow">{r.student.name} · {r.student.email}</div>}
          <h1>
            {Number(r.total_score)} <span className="of">/ {Number(r.total_marks)}</span>
          </h1>
          <div className="row">
            <span className={`status ${r.status === "graded" ? "completed" : "pending_approval"}`}>{ATTEMPT_LABEL[r.status]}</span>
            {r.passed === true && <span className="status published">Passed</span>}
            {r.passed === false && <span className="status late">Not passed</span>}
            {r.auto_submitted && <span className="chip">Auto-submitted</span>}
          </div>
        </div>
        <div className="scorecard-side">
          <TemperBar value={pct} large label="Score percentage" />
          <dl className="facts">
            <dt>Objective</dt>
            <dd className="mono">{Number(r.objective_score)}</dd>
            <dt>Written</dt>
            <dd className="mono">{Number(r.subjective_score)}</dd>
            {r.exam.pass_marks && (
              <>
                <dt>Pass mark</dt>
                <dd className="mono">{Number(r.exam.pass_marks)}</dd>
              </>
            )}
            <dt>Submitted</dt>
            <dd>{formatDate(r.submitted_at)}</dd>
          </dl>
        </div>
      </section>

      {review && r.integrity_events && r.integrity_events.length > 0 && (
        <section className="panel">
          <h2>Integrity events ({r.integrity_events.length})</h2>
          <ul className="event-list">
            {r.integrity_events.map((e, i) => (
              <li key={i}>
                <span className="mono">{formatDate(e.occurred_at)}</span> {e.kind.replace("_", " ")}
              </li>
            ))}
          </ul>
        </section>
      )}

      <ol className="cards numbered">
        {r.answers.map((a) => (
          <AnswerCard key={a.exam_question_id} answer={a} review={review} onGraded={data.reload} />
        ))}
      </ol>
    </>
  );
}

function AnswerCard({ answer: a, review, onGraded }: { answer: ResultAnswer; review: boolean; onGraded: () => void }) {
  const correct = new Set(a.correct_option_ids ?? []);
  const chosen = new Set(a.selected_option_ids);
  const verdict = a.is_correct === true ? "right" : a.is_correct === false && (chosen.size > 0 || a.type !== "subjective") ? "wrong" : "";

  return (
    <li className={`card-item answer-card ${verdict}`}>
      <div className="card-head">
        <div className="row">
          <span className="chip">{TYPE_LABEL[a.type]}</span>
        </div>
        <span className="mono">
          {a.marks_awarded === null ? "ungraded" : Number(a.marks_awarded)} / {Number(a.marks)}
        </span>
      </div>
      <p className="pre">{a.text}</p>

      {a.type !== "subjective" ? (
        <ul className="option-list">
          {a.options.map((o) => {
            const isCorrect = o.is_correct ?? correct.has(o.id);
            const picked = o.selected ?? chosen.has(o.id);
            const cls = [isCorrect && (a.correct_option_ids || review) ? "correct" : "", picked ? "picked" : ""].join(" ");
            return (
              <li key={o.id} className={cls}>
                {picked ? "● " : "○ "}
                {o.text}
                {picked && <span className="meta"> your answer</span>}
              </li>
            );
          })}
          {chosen.size === 0 && <li className="meta">Not answered</li>}
        </ul>
      ) : (
        <div className="written-answer">{a.text_answer || <span className="meta">Not answered</span>}</div>
      )}

      {a.explanation && <p className="meta">Explanation: {a.explanation}</p>}
      {!review && a.grader_feedback && <p className="notice">Feedback: {a.grader_feedback}</p>}
      {review && a.type === "subjective" && a.answer_id && a.text_answer && (
        <GradeForm answer={a} onGraded={onGraded} />
      )}
    </li>
  );
}

function GradeForm({ answer, onGraded }: { answer: ResultAnswer; onGraded: () => void }) {
  const [marks, setMarks] = useState(answer.marks_awarded ?? "");
  const [feedback, setFeedback] = useState(answer.grader_feedback);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSaved(false);
    try {
      await gradeAnswer(answer.answer_id as number, marks, feedback);
      setSaved(true);
      onGraded();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <form className="inline-form grade-form" onSubmit={onSubmit}>
      <label>
        Marks
        <input
          type="number"
          min="0"
          max={Number(answer.marks)}
          step="0.25"
          value={marks}
          onChange={(e) => setMarks(e.target.value)}
          required
        />
      </label>
      <label className="grow">
        Feedback for the student
        <input value={feedback} onChange={(e) => setFeedback(e.target.value)} />
      </label>
      <button className="small">{answer.marks_awarded === null ? "Save grade" : "Update grade"}</button>
      {saved && <span className="meta">Saved</span>}
      {error && <p className="error">{error}</p>}
    </form>
  );
}

