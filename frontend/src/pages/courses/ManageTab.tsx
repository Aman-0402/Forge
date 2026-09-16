import { useState, type FormEvent, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { errorMessage } from "../../api/client";
import {
  courseAction,
  createNode,
  deleteCourse,
  deleteNode,
  reorderNodes,
  updateNode,
  type ContentKind,
  type Course,
  type CourseTree,
} from "../../api/courses";
import { useAuth } from "../../auth/AuthContext";

type Level = "modules" | "chapters" | "lessons" | "content";

export default function ManageTab({
  course,
  tree,
  onChange,
}: {
  course: Course;
  tree: CourseTree | null;
  onChange: () => void;
}) {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function run(action: () => Promise<unknown>, after?: () => void) {
    setError("");
    setBusy(true);
    try {
      await action();
      if (after) after();
      else onChange();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const move = (level: Level, parentId: number, ids: number[], index: number, delta: number) => {
    const target = index + delta;
    if (target < 0 || target >= ids.length) return;
    const next = [...ids];
    [next[index], next[target]] = [next[target], next[index]];
    run(() => reorderNodes(level, parentId, next));
  };

  const remove = (level: Level, id: number, name: string) =>
    window.confirm(`Delete "${name}" and everything inside it?`) && run(() => deleteNode(level, id));

  const s = course.status;

  return (
    <>
      <section className="panel">
        <div className="panel-head">
          <h2>Publishing</h2>
          <Link className="button secondary small" to={`/courses/${course.id}/edit`}>
            Edit details
          </Link>
        </div>
        <p className="hint">
          {s === "draft" && "Draft courses are visible only to instructors and admins."}
          {s === "pending_approval" && "Waiting for an administrator to review and publish."}
          {s === "published" && "Students can find this course. Content changes appear immediately."}
          {s === "archived" && "Archived. Enrolled students keep read access; nobody new can join."}
        </p>
        <div className="row">
          {s === "draft" && !isAdmin && (
            <button disabled={busy} onClick={() => run(() => courseAction(course.id, "submit-for-approval"))}>
              Submit for approval
            </button>
          )}
          {isAdmin && (s === "draft" || s === "pending_approval") && (
            <button disabled={busy} onClick={() => run(() => courseAction(course.id, "approve"))}>
              Publish course
            </button>
          )}
          {isAdmin && s === "pending_approval" && (
            <button
              className="secondary"
              disabled={busy}
              onClick={() => {
                const reason = window.prompt("What should the instructor change?");
                if (reason) run(() => courseAction(course.id, "reject", { reason }));
              }}
            >
              Request changes
            </button>
          )}
          {s !== "archived" && (
            <button
              className="secondary"
              disabled={busy}
              onClick={() => window.confirm("Archive this course?") && run(() => courseAction(course.id, "archive"))}
            >
              Archive
            </button>
          )}
          {s === "draft" && course.enrollment_count === 0 && (
            <button
              className="danger"
              disabled={busy}
              onClick={() =>
                window.confirm("Delete this draft permanently?") &&
                run(() => deleteCourse(course.id), () => navigate("/courses"))
              }
            >
              Delete draft
            </button>
          )}
        </div>
        {error && <p className="error">{error}</p>}
      </section>

      <section className="panel">
        <div className="panel-head">
          <h2>Course structure</h2>
          <span className="hint">Modules hold chapters, chapters hold lessons, lessons hold material.</span>
        </div>
        {!tree && <p className="hint">Loading…</p>}
        {tree && (
          <ul className="tree-edit">
            {tree.modules.map((m, mi) => (
              <li key={m.id}>
                <Node kind="module" title={m.title}>
                  <Arrows onUp={() => move("modules", course.id, tree.modules.map((x) => x.id), mi, -1)} onDown={() => move("modules", course.id, tree.modules.map((x) => x.id), mi, 1)} />
                  <Rename level="modules" id={m.id} title={m.title} onDone={onChange} />
                  <button className="link danger" onClick={() => remove("modules", m.id, m.title)}>Delete</button>
                </Node>
                <ul>
                  {m.chapters.map((c, ci) => (
                    <li key={c.id}>
                      <Node kind="chapter" title={c.title}>
                        <Arrows onUp={() => move("chapters", m.id, m.chapters.map((x) => x.id), ci, -1)} onDown={() => move("chapters", m.id, m.chapters.map((x) => x.id), ci, 1)} />
                        <Rename level="chapters" id={c.id} title={c.title} onDone={onChange} />
                        <button className="link danger" onClick={() => remove("chapters", c.id, c.title)}>Delete</button>
                      </Node>
                      <ul>
                        {c.lessons.map((l, li) => (
                          <li key={l.id}>
                            <Node kind="lesson" title={l.title}>
                              <label className="checkbox hint">
                                <input
                                  type="checkbox"
                                  checked={l.is_preview}
                                  onChange={(e) => run(() => updateNode("lessons", l.id, { is_preview: e.target.checked }))}
                                />
                                Free preview
                              </label>
                              <Arrows onUp={() => move("lessons", c.id, c.lessons.map((x) => x.id), li, -1)} onDown={() => move("lessons", c.id, c.lessons.map((x) => x.id), li, 1)} />
                              <Rename level="lessons" id={l.id} title={l.title} onDone={onChange} />
                              <button className="link danger" onClick={() => remove("lessons", l.id, l.title)}>Delete</button>
                            </Node>
                            <ul>
                              {l.contents.map((item) => (
                                <li key={item.id}>
                                  <Node kind={item.kind} title={item.title}>
                                    {(item.file || item.url) && (
                                      <a className="hint" href={item.file ?? item.url} target="_blank" rel="noreferrer">
                                        Open
                                      </a>
                                    )}
                                    <button className="link danger" onClick={() => remove("content", item.id, item.title)}>
                                      Delete
                                    </button>
                                  </Node>
                                </li>
                              ))}
                              <li>
                                <AddContent lessonId={l.id} onDone={onChange} />
                              </li>
                            </ul>
                          </li>
                        ))}
                        <li>
                          <AddTitle level="lessons" parentId={c.id} label="lesson" onDone={onChange} />
                        </li>
                      </ul>
                    </li>
                  ))}
                  <li>
                    <AddTitle level="chapters" parentId={m.id} label="chapter" onDone={onChange} />
                  </li>
                </ul>
              </li>
            ))}
            <li>
              <AddTitle level="modules" parentId={course.id} label="module" onDone={onChange} />
            </li>
          </ul>
        )}
      </section>
    </>
  );
}

function Node({ kind, title, children }: { kind: string; title: string; children: ReactNode }) {
  return (
    <div className="tree-node">
      <span className="kind">{kind}</span>
      <span className="grow">{title}</span>
      {children}
    </div>
  );
}

function Arrows({ onUp, onDown }: { onUp: () => void; onDown: () => void }) {
  return (
    <>
      <button className="link" onClick={onUp} aria-label="Move up" title="Move up">
        ↑
      </button>
      <button className="link" onClick={onDown} aria-label="Move down" title="Move down">
        ↓
      </button>
    </>
  );
}

function Rename({ level, id, title, onDone }: { level: Level; id: number; title: string; onDone: () => void }) {
  return (
    <button
      className="link"
      onClick={async () => {
        const next = window.prompt("New title", title);
        if (next && next !== title) {
          await updateNode(level, id, { title: next });
          onDone();
        }
      }}
    >
      Rename
    </button>
  );
}

function AddTitle({
  level,
  parentId,
  label,
  onDone,
}: {
  level: Level;
  parentId: number;
  label: string;
  onDone: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [error, setError] = useState("");

  if (!open) {
    return (
      <button className="link" onClick={() => setOpen(true)}>
        + Add {label}
      </button>
    );
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await createNode(level, parentId, { title });
      setTitle("");
      setOpen(false);
      onDone();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <form className="inline-form" onSubmit={onSubmit}>
      <input autoFocus value={title} onChange={(e) => setTitle(e.target.value)} placeholder={`New ${label} title`} required />
      <button className="small">Add {label}</button>
      <button type="button" className="secondary small" onClick={() => setOpen(false)}>
        Cancel
      </button>
      {error && <p className="error">{error}</p>}
    </form>
  );
}

function AddContent({ lessonId, onDone }: { lessonId: number; onDone: () => void }) {
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<ContentKind>("pdf");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (!open) {
    return (
      <button className="link" onClick={() => setOpen(true)}>
        + Add material
      </button>
    );
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    const file = form.get("file") as File | null;
    if (!file || file.size === 0) form.delete("file");
    setError("");
    setBusy(true);
    try {
      await createNode("content", lessonId, form);
      setOpen(false);
      onDone();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const needsFile = kind === "pdf" || kind === "ppt" || kind === "doc";

  return (
    <form className="inline-form" onSubmit={onSubmit}>
      <select name="kind" value={kind} onChange={(e) => setKind(e.target.value as ContentKind)}>
        <option value="pdf">PDF</option>
        <option value="video">Video</option>
        <option value="ppt">Slides</option>
        <option value="doc">Document</option>
        <option value="link">Link</option>
        <option value="text">Reading (text)</option>
      </select>
      <input name="title" placeholder="Title" required />
      {(needsFile || kind === "video") && <input name="file" type="file" required={needsFile} />}
      {(kind === "link" || kind === "video") && (
        <input name="url" type="url" placeholder={kind === "video" ? "or video URL" : "https://…"} required={kind === "link"} />
      )}
      {kind === "text" && <textarea name="text" rows={3} placeholder="Write the reading" required />}
      <button className="small" disabled={busy}>
        {busy ? "Uploading…" : "Add material"}
      </button>
      <button type="button" className="secondary small" onClick={() => setOpen(false)}>
        Cancel
      </button>
      {error && <p className="error">{error}</p>}
    </form>
  );
}
