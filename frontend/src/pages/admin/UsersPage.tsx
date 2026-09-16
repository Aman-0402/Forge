import { useState, type FormEvent } from "react";
import {
  bulkImportUsers,
  createUser,
  deactivateUser,
  listDepartments,
  listUsers,
  resetPassword,
  updateUser,
  type AdminUser,
  type AdminUserInput,
  type BulkImportResult,
  type Department,
} from "../../api/admin";
import type { Role } from "../../api/auth";
import { errorMessage } from "../../api/client";
import Pager from "../../components/Pager";
import { useLoad } from "../../hooks/useLoad";
import { formatDate, fullName } from "../../utils/format";

const PROFILE_FIELDS: Record<Role, string[]> = {
  student: ["roll_number", "batch", "year"],
  faculty: ["employee_id", "designation"],
  admin: [],
};

export default function UsersPage() {
  const [filters, setFilters] = useState({ search: "", role: "", is_active: "" });
  const [page, setPage] = useState(1);
  const [editing, setEditing] = useState<AdminUser | "new" | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const users = useLoad(() => listUsers({ ...filters, page }), [filters, page]);
  const departments = useLoad(listDepartments, []);

  const setFilter = (key: keyof typeof filters, value: string) => {
    setFilters({ ...filters, [key]: value });
    setPage(1);
  };

  async function run(action: () => Promise<string>) {
    setMessage("");
    setError("");
    try {
      setMessage(await action());
      users.reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <>
      <div className="page-head">
        <h1>Users</h1>
        <button onClick={() => setEditing("new")}>New user</button>
      </div>

      {message && <p className="notice">{message}</p>}
      {error && <p className="error">{error}</p>}

      {editing && (
        <UserForm
          user={editing === "new" ? null : editing}
          departments={departments.data ?? []}
          onCancel={() => setEditing(null)}
          onSaved={(msg) => {
            setEditing(null);
            setMessage(msg);
            users.reload();
          }}
        />
      )}

      <div className="toolbar">
        <input
          placeholder="Search name, email, roll no."
          value={filters.search}
          onChange={(e) => setFilter("search", e.target.value)}
        />
        <select value={filters.role} onChange={(e) => setFilter("role", e.target.value)}>
          <option value="">All roles</option>
          <option value="admin">Admin</option>
          <option value="faculty">Faculty</option>
          <option value="student">Student</option>
        </select>
        <select value={filters.is_active} onChange={(e) => setFilter("is_active", e.target.value)}>
          <option value="">Active and inactive</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </select>
      </div>

      {users.error && <p className="error">{users.error}</p>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Department</th>
              <th>Status</th>
              <th>Last login</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.data?.results.map((u) => (
              <tr key={u.id} className={u.is_active ? "" : "muted"}>
                <td>{fullName(u)}</td>
                <td>{u.email}</td>
                <td>{u.role}</td>
                <td>{u.department_detail?.code ?? "—"}</td>
                <td>
                  {u.is_active ? "Active" : "Inactive"}
                  {u.must_change_password && " · temp password"}
                </td>
                <td>{formatDate(u.last_login)}</td>
                <td className="actions">
                  <button className="link" onClick={() => setEditing(u)}>
                    Edit
                  </button>
                  <button
                    className="link"
                    onClick={() =>
                      window.confirm(`Reset password for ${u.email}?`) &&
                      run(async () => {
                        const temp = await resetPassword(u.id);
                        return `New temporary password for ${u.email}: ${temp}`;
                      })
                    }
                  >
                    Reset password
                  </button>
                  {u.is_active ? (
                    <button
                      className="link danger"
                      onClick={() =>
                        window.confirm(`Deactivate ${u.email}? They will be signed out.`) &&
                        run(async () => {
                          await deactivateUser(u.id);
                          return `${u.email} deactivated.`;
                        })
                      }
                    >
                      Deactivate
                    </button>
                  ) : (
                    <button
                      className="link"
                      onClick={() =>
                        run(async () => {
                          await updateUser(u.id, { is_active: true });
                          return `${u.email} reactivated.`;
                        })
                      }
                    >
                      Activate
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {users.loading && <p>Loading…</p>}
      {users.data && <Pager page={page} count={users.data.count} onPage={setPage} />}

      <BulkImport onDone={users.reload} />
    </>
  );
}

function UserForm({
  user,
  departments,
  onCancel,
  onSaved,
}: {
  user: AdminUser | null;
  departments: Department[];
  onCancel: () => void;
  onSaved: (message: string) => void;
}) {
  const [form, setForm] = useState({
    email: user?.email ?? "",
    first_name: user?.first_name ?? "",
    last_name: user?.last_name ?? "",
    phone: user?.phone ?? "",
    role: (user?.role ?? "student") as Role,
    department: user?.department ? String(user.department) : "",
  });
  const [profile, setProfile] = useState<Record<string, string>>(
    Object.fromEntries(
      Object.entries(user?.profile ?? {}).map(([k, v]) => [k, v === null ? "" : String(v)]),
    ),
  );
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (key: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm({ ...form, [key]: e.target.value });

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    const profileBody = Object.fromEntries(
      PROFILE_FIELDS[form.role].map((k) => [k, profile[k] ? profile[k] : null]),
    );
    const body: AdminUserInput = {
      ...form,
      department: form.department ? Number(form.department) : null,
      profile: profileBody,
    };
    try {
      if (user) {
        await updateUser(user.id, body);
        onSaved(`${form.email} updated.`);
      } else {
        const created = await createUser(body);
        onSaved(
          created.temp_password
            ? `${created.email} created. Temporary password: ${created.temp_password}`
            : `${created.email} created.`,
        );
      }
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel" onSubmit={onSubmit}>
      <h2>{user ? `Edit ${user.email}` : "New user"}</h2>
      <div className="grid">
        <label>
          Email
          <input type="email" value={form.email} onChange={set("email")} required />
        </label>
        <label>
          Role
          <select value={form.role} onChange={set("role")}>
            <option value="student">Student</option>
            <option value="faculty">Faculty</option>
            <option value="admin">Admin</option>
          </select>
        </label>
        <label>
          First name
          <input value={form.first_name} onChange={set("first_name")} />
        </label>
        <label>
          Last name
          <input value={form.last_name} onChange={set("last_name")} />
        </label>
        <label>
          Phone
          <input value={form.phone} onChange={set("phone")} />
        </label>
        <label>
          Department
          <select value={form.department} onChange={set("department")}>
            <option value="">None</option>
            {departments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.code} — {d.name}
              </option>
            ))}
          </select>
        </label>
        {PROFILE_FIELDS[form.role].map((field) => (
          <label key={field}>
            {field.replace("_", " ")}
            <input
              value={profile[field] ?? ""}
              onChange={(e) => setProfile({ ...profile, [field]: e.target.value })}
            />
          </label>
        ))}
      </div>
      {!user && (
        <p className="hint">A temporary password is generated and shown after saving.</p>
      )}
      {error && <p className="error">{error}</p>}
      <div className="row">
        <button disabled={busy}>{busy ? "Saving…" : "Save"}</button>
        <button type="button" className="secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}

function BulkImport({ onDone }: { onDone: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<BulkImportResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!file) return;
    setError("");
    setResult(null);
    setBusy(true);
    try {
      setResult(await bulkImportUsers(file));
      onDone();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="panel" onSubmit={onSubmit}>
      <h2>Bulk import (CSV)</h2>
      <p className="hint">
        Required columns: <code>email</code>, <code>role</code>. Optional: first_name, last_name,
        phone, department_code, roll_number, batch, year, employee_id, designation.
      </p>
      <div className="row">
        <input type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <button disabled={!file || busy}>{busy ? "Importing…" : "Import"}</button>
      </div>
      {error && <p className="error">{error}</p>}
      {result && (
        <>
          <p className="notice">
            Created {result.created.length}, failed {result.errors.length}.
          </p>
          {result.created.length > 0 && (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Row</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Temporary password</th>
                  </tr>
                </thead>
                <tbody>
                  {result.created.map((c) => (
                    <tr key={c.row}>
                      <td>{c.row}</td>
                      <td>{c.email}</td>
                      <td>{c.role}</td>
                      <td>
                        <code>{c.temp_password}</code>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {result.errors.length > 0 && (
            <ul className="error-list">
              {result.errors.map((e) => (
                <li key={e.row}>
                  Row {e.row}: {JSON.stringify(e.errors)}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </form>
  );
}
