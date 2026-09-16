import { useState } from "react";
import { listAuditLogs } from "../../api/admin";
import Pager from "../../components/Pager";
import { useLoad } from "../../hooks/useLoad";
import { formatDate } from "../../utils/format";

export default function AuditLogPage() {
  const [action, setAction] = useState("");
  const [page, setPage] = useState(1);
  const logs = useLoad(() => listAuditLogs({ action, page }), [action, page]);

  return (
    <>
      <h1>Audit log</h1>
      <div className="toolbar">
        <input
          placeholder="Exact action, e.g. user.create"
          value={action}
          onChange={(e) => {
            setAction(e.target.value.trim());
            setPage(1);
          }}
        />
      </div>
      {logs.error && <p className="error">{logs.error}</p>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>When</th>
              <th>Actor</th>
              <th>Action</th>
              <th>Target</th>
              <th>Details</th>
              <th>IP</th>
            </tr>
          </thead>
          <tbody>
            {logs.data?.results.map((l) => (
              <tr key={l.id}>
                <td>{formatDate(l.created_at)}</td>
                <td>{l.actor_email ?? "system"}</td>
                <td>
                  <code>{l.action}</code>
                </td>
                <td>{l.target_type ? `${l.target_type} #${l.target_id}` : "—"}</td>
                <td>
                  <code>{Object.keys(l.metadata).length ? JSON.stringify(l.metadata) : ""}</code>
                </td>
                <td>{l.ip ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {logs.data && <Pager page={page} count={logs.data.count} onPage={setPage} />}
    </>
  );
}
