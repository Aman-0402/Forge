import { useState } from "react";
import { Link } from "react-router-dom";
import { errorMessage } from "../../api/client";
import { courseAction, listCourses } from "../../api/courses";
import { useLoad } from "../../hooks/useLoad";
import { formatDate } from "../../utils/format";
import { promptDialog, toast } from "../../utils/notify";

export default function ApprovalsPage() {
  const list = useLoad(() => listCourses({ status: "pending_approval", page_size: 50 }), []);
  const [error, setError] = useState("");

  async function act(id: number, title: string, action: "approve" | "reject") {
    setError("");
    try {
      if (action === "reject") {
        const reason = await promptDialog({ title: `What should change in "${title}"?` });
        if (!reason) return;
        await courseAction(id, "reject", { reason });
        toast.success(`Changes requested for "${title}".`);
      } else {
        await courseAction(id, "approve");
        toast.success(`"${title}" is published.`);
      }
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
          <h1>Course approvals</h1>
        </div>
      </div>
      {(error || list.error) && <p className="error">{error || list.error}</p>}
      {list.data?.results.length === 0 && (
        <div className="empty">
          <strong>Nothing waiting</strong>
          Courses submitted by faculty show up here.
        </div>
      )}
      {list.data && list.data.results.length > 0 && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Course</th>
                <th>Instructor</th>
                <th className="num">Lessons</th>
                <th>Submitted</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {list.data.results.map((c) => (
                <tr key={c.id}>
                  <td>
                    <Link to={`/courses/${c.id}`}>{c.title}</Link>
                    {c.code && <div className="meta mono">{c.code}</div>}
                  </td>
                  <td>{c.instructor_detail.name}</td>
                  <td className="num">{c.lesson_count}</td>
                  <td>{formatDate(c.submitted_at)}</td>
                  <td className="actions">
                    <div className="row">
                      <button className="small" onClick={() => act(c.id, c.title, "approve")}>
                        Publish
                      </button>
                      <button className="secondary small" onClick={() => act(c.id, c.title, "reject")}>
                        Request changes
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
