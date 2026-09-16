import { useState, type FormEvent } from "react";
import {
  createMarketingStat,
  deleteMarketingStat,
  listAllMarketingStats,
  updateMarketingStat,
  type MarketingStat,
} from "../../api/admin";
import { errorMessage } from "../../api/client";
import { useLoad } from "../../hooks/useLoad";
import { confirmDialog, toast } from "../../utils/notify";

const empty = { order: 0, value: "", suffix: "", description: "" };

export default function MarketingStatsPage() {
  const stats = useLoad(listAllMarketingStats, []);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState<number | null>(null);
  const [error, setError] = useState("");

  function startEdit(stat: MarketingStat) {
    setEditing(stat.id);
    setForm({ order: stat.order, value: stat.value, suffix: stat.suffix, description: stat.description });
  }

  function cancelEdit() {
    setEditing(null);
    setForm(empty);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    const wasEditing = editing !== null;
    try {
      if (editing) await updateMarketingStat(editing, form);
      else await createMarketingStat(form);
      cancelEdit();
      stats.reload();
      toast.success(wasEditing ? "Stat updated." : "Stat added to the public site.");
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function onDelete(id: number) {
    if (!(await confirmDialog({ title: "Delete this stat from the public site?", danger: true }))) return;
    setError("");
    try {
      await deleteMarketingStat(id);
      stats.reload();
      toast.success("Stat deleted.");
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <>
      <h1>Marketing site stats</h1>
      <p className="hint">
        The three highlight numbers on the public home page (dsaforge.example/#stats). Lower order
        shows first.
      </p>

      <form className="panel" onSubmit={onSubmit}>
        <h2>{editing ? "Edit stat" : "New stat"}</h2>
        <div className="grid">
          <label>
            Order
            <input
              type="number"
              value={form.order}
              onChange={(e) => setForm({ ...form, order: Number(e.target.value) })}
            />
          </label>
          <label>
            Value
            <input
              placeholder="95"
              value={form.value}
              onChange={(e) => setForm({ ...form, value: e.target.value })}
              required
            />
          </label>
          <label>
            Suffix
            <input
              placeholder="%"
              value={form.suffix}
              onChange={(e) => setForm({ ...form, suffix: e.target.value })}
            />
          </label>
          <label>
            Description
            <input
              placeholder="learn more consistently with guided practice"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </label>
        </div>
        {error && <p className="error">{error}</p>}
        <div className="row">
          <button>{editing ? "Save" : "Add stat"}</button>
          {editing && (
            <button type="button" className="secondary" onClick={cancelEdit}>
              Cancel
            </button>
          )}
        </div>
      </form>

      {stats.error && <p className="error">{stats.error}</p>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Order</th>
              <th>Value</th>
              <th>Description</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {stats.data?.map((s) => (
              <tr key={s.id}>
                <td>{s.order}</td>
                <td>
                  {s.value}
                  {s.suffix}
                </td>
                <td>{s.description}</td>
                <td className="actions">
                  <button className="link" onClick={() => startEdit(s)}>
                    Edit
                  </button>
                  <button className="link danger" onClick={() => onDelete(s.id)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
