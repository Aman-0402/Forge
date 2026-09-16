import { useState } from "react";
import { Link } from "react-router-dom";
import { listProblems } from "../../api/coding";
import { useAuth } from "../../auth/AuthContext";
import Pager from "../../components/Pager";
import { useLoad } from "../../hooks/useLoad";
import { DIFFICULTY_LABEL } from "../../utils/codingLabels";

export default function ProblemsPage() {
  const { user } = useAuth();
  const staff = user?.role === "admin" || user?.role === "faculty";
  const [filters, setFilters] = useState({ search: "", difficulty: "", status: "" });
  const [page, setPage] = useState(1);
  const problems = useLoad(() => listProblems({ ...filters, page }), [filters, page]);

  const set = (key: keyof typeof filters) => (e: { target: { value: string } }) => {
    setFilters({ ...filters, [key]: e.target.value });
    setPage(1);
  };

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">Coding portal</div>
          <h1>Problems</h1>
        </div>
        {staff && (
          <Link className="button" to="/problems/new">
            New problem
          </Link>
        )}
      </div>

      <div className="toolbar">
        <input type="search" placeholder="Search problems" value={filters.search} onChange={set("search")} />
        <select value={filters.difficulty} onChange={set("difficulty")} aria-label="Difficulty">
          <option value="">Any difficulty</option>
          <option value="easy">Easy</option>
          <option value="medium">Medium</option>
          <option value="hard">Hard</option>
        </select>
        {staff && (
          <select value={filters.status} onChange={set("status")} aria-label="Status">
            <option value="">Any status</option>
            <option value="draft">Draft</option>
            <option value="published">Published</option>
            <option value="archived">Archived</option>
          </select>
        )}
      </div>

      {problems.error && <p className="error">{problems.error}</p>}
      {problems.data?.results.length === 0 && (
        <div className="empty">
          <strong>No problems</strong>
          {staff ? "Write a problem, add test cases, then publish it." : "Problems your instructors publish appear here."}
        </div>
      )}
      {problems.data && problems.data.results.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Problem</th>
                <th>Difficulty</th>
                <th>Tags</th>
                <th className="num">Points</th>
                <th>{staff ? "Status" : "Your best"}</th>
              </tr>
            </thead>
            <tbody>
              {problems.data.results.map((p) => (
                <tr key={p.id}>
                  <td>
                    <Link to={`/problems/${p.id}`}>{p.title}</Link>
                    {p.course_title && <div className="meta">{p.course_title}</div>}
                  </td>
                  <td>
                    <span className={`difficulty ${p.difficulty}`}>{DIFFICULTY_LABEL[p.difficulty]}</span>
                  </td>
                  <td>
                    <div className="row">
                      {p.tags.map((t) => (
                        <span key={t} className="chip">
                          {t}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="num">{p.max_score}</td>
                  <td>
                    {staff ? (
                      <span className={`status ${p.status === "published" ? "published" : p.status === "draft" ? "draft" : "archived"}`}>
                        {p.status}
                      </span>
                    ) : p.my_status?.solved ? (
                      <span className="status published">Solved</span>
                    ) : p.my_status && p.my_status.attempts > 0 ? (
                      <span className="mono">
                        {p.my_status.best_score}/{p.max_score}
                      </span>
                    ) : (
                      <span className="meta">Not tried</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {problems.data && <Pager page={page} count={problems.data.count} onPage={setPage} />}
    </>
  );
}
