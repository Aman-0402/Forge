import { Link, useParams } from "react-router-dom";
import { getSubmission } from "../../api/coding";
import CodeEditor from "../../components/CodeEditor";
import { useLoad } from "../../hooks/useLoad";
import { VERDICT_CLASS, VERDICT_LABEL } from "../../utils/codingLabels";
import { formatDate } from "../../utils/format";

export default function SubmissionPage() {
  const id = Number(useParams().id);
  const data = useLoad(() => getSubmission(id), [id]);
  const s = data.data;

  if (data.error) return <p className="error">{data.error}</p>;
  if (!s) return <p className="hint">Loading submission…</p>;

  const lines = s.source_code.split("\n").length;

  return (
    <>
      <div className="eyebrow">
        <Link to={`/problems/${s.problem}?tab=submissions`}>{s.problem_title}</Link> / Submission
      </div>
      <div className="page-head">
        <div>
          <div className="row">
            {s.verdict && <span className={`status ${VERDICT_CLASS[s.verdict]}`}>{VERDICT_LABEL[s.verdict]}</span>}
            <span className="chip">{s.language_name}</span>
          </div>
          <h1>
            {s.score} pts <span className="meta">· {s.passed_count}/{s.total_count} tests</span>
          </h1>
          <p className="meta">
            {s.student_name} · submitted {formatDate(s.submitted_at)}
            {s.max_time_seconds && ` · ${Number(s.max_time_seconds)}s`}
            {s.max_memory_kb && ` · ${Math.round(s.max_memory_kb / 1024)} MB`}
          </p>
        </div>
      </div>

      <section className="panel code-panel">
        <CodeEditor value={s.source_code} language={s.language_name.toLowerCase().replace("c++", "cpp")} readOnly height={Math.min(600, 22 * lines + 40)} />
      </section>

      {s.compile_output && (
        <section className="panel">
          <h2>Compiler output</h2>
          <pre className="compile">{s.compile_output}</pre>
        </section>
      )}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Result</th>
              <th>Input</th>
              <th>Expected</th>
              <th>Your output</th>
              <th className="num">Time</th>
            </tr>
          </thead>
          <tbody>
            {s.results.map((r) => (
              <tr key={r.index}>
                <td className="mono">{r.index}</td>
                <td>
                  <span className={`status ${VERDICT_CLASS[r.verdict]}`}>{VERDICT_LABEL[r.verdict]}</span>
                </td>
                {r.input === undefined ? (
                  <td colSpan={3} className="meta">
                    Hidden test case
                  </td>
                ) : (
                  <>
                    <td>
                      <pre className="cell">{r.input}</pre>
                    </td>
                    <td>
                      <pre className="cell">{r.expected_output}</pre>
                    </td>
                    <td>
                      <pre className="cell">{r.stdout || r.stderr}</pre>
                    </td>
                  </>
                )}
                <td className="num">{r.time_seconds ? `${Number(r.time_seconds)}s` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
