import { useState } from "react";
import { errorMessage } from "../api/client";
import { listNotifications, markAllRead, markRead } from "../api/notifications";
import Pager from "../components/Pager";
import { useLoad } from "../hooks/useLoad";
import { formatDate } from "../utils/format";

export default function NotificationsPage() {
  const [unread, setUnread] = useState(false);
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const list = useLoad(
    () => listNotifications({ unread: unread || undefined, page }),
    [unread, page],
  );

  async function run(action: () => Promise<unknown>) {
    setError("");
    try {
      await action();
      list.reload();
      window.dispatchEvent(new Event("forge:notifications-changed"));
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <>
      <div className="page-head">
        <h1>Notifications</h1>
        <button className="secondary" onClick={() => run(markAllRead)}>
          Mark all read
        </button>
      </div>
      <label className="checkbox">
        <input
          type="checkbox"
          checked={unread}
          onChange={(e) => {
            setUnread(e.target.checked);
            setPage(1);
          }}
        />
        Unread only
      </label>
      {(error || list.error) && <p className="error">{error || list.error}</p>}
      {list.data?.results.length === 0 && <p>No notifications.</p>}
      <ul className="cards">
        {list.data?.results.map((n) => (
          <li key={n.id} className={n.is_read ? "card-item read" : "card-item"}>
            <div className="card-head">
              <strong>{n.title}</strong>
              <span className="meta">
                {n.kind} · {formatDate(n.created_at)}
              </span>
            </div>
            {n.body && <p className="pre">{n.body}</p>}
            {!n.is_read && (
              <button className="link" onClick={() => run(() => markRead(n.id))}>
                Mark read
              </button>
            )}
          </li>
        ))}
      </ul>
      {list.data && <Pager page={page} count={list.data.count} onPage={setPage} />}
    </>
  );
}
