import { useState } from "react";
import { listContactMessages } from "../../api/admin";
import Pager from "../../components/Pager";
import { useLoad } from "../../hooks/useLoad";
import { formatDate } from "../../utils/format";

export default function ContactMessagesPage() {
  const [page, setPage] = useState(1);
  const messages = useLoad(() => listContactMessages({ page }), [page]);

  return (
    <>
      <div className="page-head">
        <h1>Contact messages</h1>
      </div>
      <p className="hint">Submitted from the public contact form. Every active admin was emailed.</p>
      {messages.error && <p className="error">{messages.error}</p>}
      {!messages.loading && messages.data?.count === 0 && (
        <p className="empty">
          <strong>No messages yet</strong>
          Visitor messages from /contact will show up here.
        </p>
      )}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>When</th>
              <th>Name</th>
              <th>Email</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            {messages.data?.results.map((m) => (
              <tr key={m.id}>
                <td>{formatDate(m.created_at)}</td>
                <td>{m.name}</td>
                <td>
                  <a href={`mailto:${m.email}`}>{m.email}</a>
                </td>
                <td className="pre">{m.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {messages.data && <Pager page={page} count={messages.data.count} onPage={setPage} />}
    </>
  );
}
