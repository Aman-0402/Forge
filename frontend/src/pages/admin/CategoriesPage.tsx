import { useState, type FormEvent } from "react";
import { api, errorMessage } from "../../api/client";
import { createCategory, listCategories } from "../../api/courses";
import { useLoad } from "../../hooks/useLoad";
import { confirmDialog } from "../../utils/notify";

export default function CategoriesPage() {
  const list = useLoad(listCategories, []);
  const [name, setName] = useState("");
  const [kind, setKind] = useState("subject");
  const [error, setError] = useState("");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await createCategory({ name, kind });
      setName("");
      list.reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function remove(id: number, label: string) {
    if (!(await confirmDialog({ title: `Delete category "${label}"? Courses keep their other categories.`, danger: true }))) return;
    try {
      await api.delete(`/categories/${id}/`);
      list.reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <>
      <div className="page-head">
        <div>
          <div className="eyebrow">Administration</div>
          <h1>Course categories</h1>
        </div>
      </div>
      <form className="panel inline-form" onSubmit={onSubmit}>
        <label>
          Name
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label>
          Type
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="subject">Subject</option>
            <option value="department">Department</option>
            <option value="level">Level</option>
          </select>
        </label>
        <button>Add category</button>
      </form>
      {(error || list.error) && <p className="error">{error || list.error}</p>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Type</th>
              <th>Slug</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {list.data?.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td>{c.kind}</td>
                <td className="mono">{c.slug}</td>
                <td className="actions">
                  <button className="link danger" onClick={() => remove(c.id, c.name)}>
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
