import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { errorMessage } from "../../api/client";
import { createBank, listBanks } from "../../api/exams";
import Pager from "../../components/Pager";
import { useLoad } from "../../hooks/useLoad";

export default function BanksPage() {
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const banks = useLoad(() => listBanks({ search, page }), [search, page]);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", is_shared: false });
  const [error, setError] = useState("");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await createBank(form);
      setForm({ title: "", description: "", is_shared: false });
      setCreating(false);
      banks.reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">Assessment</div>
          <h1>Question banks</h1>
        </div>
        {!creating && <button onClick={() => setCreating(true)}>New bank</button>}
      </div>

      {creating && (
        <form className="panel" onSubmit={onSubmit}>
          <h2>New question bank</h2>
          <div className="grid">
            <label>
              Title
              <input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} required />
            </label>
            <label>
              Description
              <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </label>
          </div>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={form.is_shared}
              onChange={(e) => setForm({ ...form, is_shared: e.target.checked })}
            />
            Share with other faculty (they can use questions, not edit them)
          </label>
          {error && <p className="error">{error}</p>}
          <div className="row">
            <button>Create bank</button>
            <button type="button" className="secondary" onClick={() => setCreating(false)}>
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="toolbar">
        <input
          type="search"
          placeholder="Search banks"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />
      </div>
      {banks.error && <p className="error">{banks.error}</p>}
      {banks.data?.results.length === 0 && (
        <div className="empty">
          <strong>No question banks</strong>
          Create a bank to start writing questions.
        </div>
      )}
      {banks.data && banks.data.results.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Bank</th>
                <th>Owner</th>
                <th className="num">Questions</th>
                <th>Sharing</th>
              </tr>
            </thead>
            <tbody>
              {banks.data.results.map((b) => (
                <tr key={b.id}>
                  <td>
                    <Link to={`/question-banks/${b.id}`}>{b.title}</Link>
                    {b.description && <div className="meta">{b.description}</div>}
                  </td>
                  <td>{b.owner_name}</td>
                  <td className="num">{b.question_count}</td>
                  <td>{b.is_shared ? <span className="chip">Shared</span> : <span className="meta">Private</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {banks.data && <Pager page={page} count={banks.data.count} onPage={setPage} />}
    </>
  );
}
