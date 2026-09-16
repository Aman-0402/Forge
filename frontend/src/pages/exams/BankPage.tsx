import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { errorMessage } from "../../api/client";
import {
  createQuestion,
  deleteQuestion,
  getBank,
  importQuestions,
  listQuestions,
  updateQuestion,
  type Difficulty,
  type OptionInput,
  type QuestionType,
} from "../../api/exams";
import Pager from "../../components/Pager";
import { useLoad } from "../../hooks/useLoad";
import { TYPE_LABEL } from "../../utils/examLabels";
import { confirmDialog } from "../../utils/notify";

export default function BankPage() {
  const id = Number(useParams().id);
  const { user } = useAuth();
  const bank = useLoad(() => getBank(id), [id]);
  const [filters, setFilters] = useState({ type: "", difficulty: "", search: "" });
  const [page, setPage] = useState(1);
  const questions = useLoad(() => listQuestions(id, { ...filters, page }), [id, filters, page]);
  const [mode, setMode] = useState<"none" | "add" | "import">("none");
  const [error, setError] = useState("");

  const canEdit = bank.data && (user?.role === "admin" || bank.data.owner === user?.id);

  async function run(action: () => Promise<unknown>) {
    setError("");
    try {
      await action();
      questions.reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  const set = (key: keyof typeof filters) => (e: { target: { value: string } }) => {
    setFilters({ ...filters, [key]: e.target.value });
    setPage(1);
  };

  return (
    <>
      <div className="eyebrow">
        <Link to="/question-banks">Question banks</Link>
      </div>
      <div className="page-head">
        <div>
          <h1>{bank.data?.title ?? "Question bank"}</h1>
          {bank.data?.description && <p className="lede">{bank.data.description}</p>}
        </div>
        {canEdit && (
          <div className="row">
            <button onClick={() => setMode(mode === "add" ? "none" : "add")}>Add question</button>
            <button className="secondary" onClick={() => setMode(mode === "import" ? "none" : "import")}>
              Import JSON
            </button>
          </div>
        )}
      </div>

      {mode === "add" && (
        <QuestionForm
          onCancel={() => setMode("none")}
          onSave={async (body) => {
            await createQuestion(id, body);
            setMode("none");
            questions.reload();
          }}
        />
      )}
      {mode === "import" && (
        <ImportForm
          onCancel={() => setMode("none")}
          onImport={async (items) => {
            const res = await importQuestions(id, items);
            setMode("none");
            questions.reload();
            return res.created;
          }}
        />
      )}

      <div className="toolbar">
        <input type="search" placeholder="Search question text" value={filters.search} onChange={set("search")} />
        <select value={filters.type} onChange={set("type")} aria-label="Type">
          <option value="">All types</option>
          {Object.entries(TYPE_LABEL).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <select value={filters.difficulty} onChange={set("difficulty")} aria-label="Difficulty">
          <option value="">Any difficulty</option>
          <option value="easy">Easy</option>
          <option value="medium">Medium</option>
          <option value="hard">Hard</option>
        </select>
      </div>

      {(error || questions.error) && <p className="error">{error || questions.error}</p>}
      {questions.data?.results.length === 0 && (
        <div className="empty">
          <strong>No questions</strong>
          {canEdit ? "Add a question or import a batch." : "This bank has no questions yet."}
        </div>
      )}
      <ul className="cards">
        {questions.data?.results.map((q) => (
          <li key={q.id} className={q.is_active ? "card-item" : "card-item read"}>
            <div className="card-head">
              <div className="row">
                <span className="chip">{TYPE_LABEL[q.type]}</span>
                <span className="chip">{q.difficulty}</span>
                <span className="chip mono">
                  {Number(q.marks)} marks{Number(q.negative_marks) > 0 && ` · −${Number(q.negative_marks)}`}
                </span>
                {!q.is_active && <span className="status archived">Inactive</span>}
                {q.used_in_exams ? <span className="meta">Used in {q.used_in_exams} exams</span> : null}
              </div>
              {canEdit && (
                <div className="row">
                  <button
                    className="link"
                    onClick={() => run(() => updateQuestion(q.id, { is_active: !q.is_active }))}
                  >
                    {q.is_active ? "Deactivate" : "Activate"}
                  </button>
                  <button
                    className="link danger"
                    onClick={async () => {
                      if (await confirmDialog({ title: "Delete this question?", danger: true })) {
                        run(() => deleteQuestion(q.id));
                      }
                    }}
                  >
                    Delete
                  </button>
                </div>
              )}
            </div>
            <p className="pre">{q.text}</p>
            {q.options.length > 0 && (
              <ul className="option-list">
                {q.options.map((o) => (
                  <li key={o.id} className={o.is_correct ? "correct" : ""}>
                    {o.is_correct ? "✓ " : ""}
                    {o.text}
                  </li>
                ))}
              </ul>
            )}
            {q.explanation && <p className="meta">Explanation: {q.explanation}</p>}
          </li>
        ))}
      </ul>
      {questions.data && <Pager page={page} count={questions.data.count} onPage={setPage} />}
    </>
  );
}

const BLANK_OPTIONS: OptionInput[] = [
  { text: "", is_correct: true },
  { text: "", is_correct: false },
  { text: "", is_correct: false },
  { text: "", is_correct: false },
];

function QuestionForm({
  onSave,
  onCancel,
}: {
  onSave: (body: Parameters<typeof createQuestion>[1]) => Promise<void>;
  onCancel: () => void;
}) {
  const [type, setType] = useState<QuestionType>("mcq_single");
  const [text, setText] = useState("");
  const [marks, setMarks] = useState("1");
  const [negative, setNegative] = useState("0");
  const [difficulty, setDifficulty] = useState<Difficulty>("medium");
  const [explanation, setExplanation] = useState("");
  const [tags, setTags] = useState("");
  const [options, setOptions] = useState<OptionInput[]>(BLANK_OPTIONS);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function changeType(next: QuestionType) {
    setType(next);
    if (next === "true_false") {
      setOptions([
        { text: "True", is_correct: true },
        { text: "False", is_correct: false },
      ]);
    } else if (type === "true_false") {
      setOptions(BLANK_OPTIONS);
    }
  }

  function toggleCorrect(index: number) {
    setOptions(
      options.map((o, i) =>
        type === "mcq_multi" ? (i === index ? { ...o, is_correct: !o.is_correct } : o) : { ...o, is_correct: i === index },
      ),
    );
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await onSave({
        type,
        text,
        marks,
        negative_marks: negative,
        difficulty,
        explanation,
        tags: tags.split(",").map((t) => t.trim()).filter(Boolean),
        options: type === "subjective" ? [] : options.filter((o) => o.text.trim()),
      });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel" onSubmit={onSubmit}>
      <h2>New question</h2>
      <div className="grid">
        <label>
          Type
          <select value={type} onChange={(e) => changeType(e.target.value as QuestionType)}>
            {Object.entries(TYPE_LABEL).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Marks
          <input type="number" min="0" step="0.25" value={marks} onChange={(e) => setMarks(e.target.value)} required />
        </label>
        <label>
          Negative marks (wrong answer)
          <input
            type="number"
            min="0"
            step="0.25"
            value={negative}
            disabled={type === "subjective"}
            onChange={(e) => setNegative(e.target.value)}
          />
        </label>
        <label>
          Difficulty
          <select value={difficulty} onChange={(e) => setDifficulty(e.target.value as Difficulty)}>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </label>
      </div>
      <label>
        Question
        <textarea rows={3} value={text} onChange={(e) => setText(e.target.value)} required />
      </label>
      {type !== "subjective" && (
        <fieldset className="options-edit">
          <legend>Options — mark the correct {type === "mcq_multi" ? "answers" : "answer"}</legend>
          {options.map((o, i) => (
            <div key={i} className="row">
              <input
                type={type === "mcq_multi" ? "checkbox" : "radio"}
                name="correct"
                checked={o.is_correct}
                onChange={() => toggleCorrect(i)}
                aria-label={`Option ${i + 1} is correct`}
              />
              <input
                className="grow"
                value={o.text}
                readOnly={type === "true_false"}
                onChange={(e) => setOptions(options.map((x, j) => (j === i ? { ...x, text: e.target.value } : x)))}
                placeholder={`Option ${i + 1}`}
              />
              {type !== "true_false" && options.length > 2 && (
                <button type="button" className="link danger" onClick={() => setOptions(options.filter((_, j) => j !== i))}>
                  Remove
                </button>
              )}
            </div>
          ))}
          {type !== "true_false" && options.length < 8 && (
            <button type="button" className="link" onClick={() => setOptions([...options, { text: "", is_correct: false }])}>
              + Add option
            </button>
          )}
        </fieldset>
      )}
      <div className="grid">
        <label>
          Explanation (shown after results if you allow it)
          <input value={explanation} onChange={(e) => setExplanation(e.target.value)} />
        </label>
        <label>
          Tags (comma separated)
          <input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="arrays, sorting" />
        </label>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="row">
        <button disabled={busy}>{busy ? "Saving…" : "Save question"}</button>
        <button type="button" className="secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}

const IMPORT_EXAMPLE = `[
  {
    "type": "mcq_single",
    "text": "Which structure is LIFO?",
    "marks": "1",
    "difficulty": "easy",
    "options": [
      {"text": "Queue", "is_correct": false},
      {"text": "Stack", "is_correct": true}
    ]
  },
  {"type": "subjective", "text": "Explain binary search.", "marks": "5"}
]`;

function ImportForm({
  onImport,
  onCancel,
}: {
  onImport: (items: unknown[]) => Promise<number>;
  onCancel: () => void;
}) {
  const [json, setJson] = useState(IMPORT_EXAMPLE);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    let items: unknown;
    try {
      items = JSON.parse(json);
    } catch {
      setError("That is not valid JSON.");
      return;
    }
    if (!Array.isArray(items)) {
      setError("Paste a JSON array of questions.");
      return;
    }
    setBusy(true);
    try {
      await onImport(items);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel" onSubmit={onSubmit}>
      <h2>Import questions</h2>
      <p className="hint">Paste a JSON array. Nothing is saved unless every question is valid.</p>
      <textarea className="mono" rows={14} value={json} onChange={(e) => setJson(e.target.value)} />
      {error && <p className="error">{error}</p>}
      <div className="row">
        <button disabled={busy}>{busy ? "Importing…" : "Import"}</button>
        <button type="button" className="secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
