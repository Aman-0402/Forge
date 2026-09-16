import { useState, type FormEvent } from "react";
import { createDepartment, deleteDepartment, listDepartments } from "../../api/admin";
import { errorMessage } from "../../api/client";
import { useLoad } from "../../hooks/useLoad";
import { confirmDialog } from "../../utils/notify";

export default function DepartmentsPage() {
  const departments = useLoad(listDepartments, []);
  const [form, setForm] = useState({ name: "", code: "", description: "" });
  const [error, setError] = useState("");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await createDepartment(form);
      setForm({ name: "", code: "", description: "" });
      departments.reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function onDelete(id: number, code: string) {
    if (!(await confirmDialog({ title: `Delete department ${code}? Users keep their accounts.`, danger: true }))) return;
    setError("");
    try {
      await deleteDepartment(id);
      departments.reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <>
      <h1>Departments</h1>
      <form className="panel" onSubmit={onSubmit}>
        <h2>New department</h2>
        <div className="grid">
          <label>
            Code
            <input
              value={form.code}
              onChange={(e) => setForm({ ...form, code: e.target.value })}
              required
            />
          </label>
          <label>
            Name
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
          </label>
          <label>
            Description
            <input
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </label>
        </div>
        <button>Add department</button>
      </form>

      {error && <p className="error">{error}</p>}
      {departments.error && <p className="error">{departments.error}</p>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>Description</th>
              <th>Users</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {departments.data?.map((d) => (
              <tr key={d.id}>
                <td>{d.code}</td>
                <td>{d.name}</td>
                <td>{d.description}</td>
                <td>{d.user_count}</td>
                <td>
                  <button className="link danger" onClick={() => onDelete(d.id, d.code)}>
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
