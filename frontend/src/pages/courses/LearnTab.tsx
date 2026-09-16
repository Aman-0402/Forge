import { useMemo, useRef, useState } from "react";
import { errorMessage } from "../../api/client";
import {
  completeLesson,
  saveLessonPosition,
  type ContentItem,
  type CourseTree,
  type TreeLesson,
} from "../../api/courses";

const KIND_LABEL: Record<ContentItem["kind"], string> = {
  video: "Video",
  pdf: "PDF",
  ppt: "Slides",
  doc: "Document",
  link: "Link",
  text: "Reading",
};

export default function LearnTab({
  tree,
  error,
  canTrack,
  onProgress,
}: {
  tree: CourseTree | null;
  error: string;
  canTrack: boolean;
  onProgress: () => void;
}) {
  const lessons = useMemo(
    () => tree?.modules.flatMap((m) => m.chapters.flatMap((c) => c.lessons)) ?? [],
    [tree],
  );
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [actionError, setActionError] = useState("");
  const [busy, setBusy] = useState(false);

  if (error) return <p className="error">{error}</p>;
  if (!tree) return <p className="hint">Loading content…</p>;
  if (lessons.length === 0) {
    return (
      <div className="empty">
        <strong>No lessons yet</strong>
        Lessons appear here once the instructor adds them.
      </div>
    );
  }

  const firstOpen = lessons.find((l) => !l.locked && !l.completed) ?? lessons.find((l) => !l.locked);
  const selected = lessons.find((l) => l.id === selectedId) ?? firstOpen ?? null;
  const index = selected ? lessons.indexOf(selected) : -1;
  const next = lessons.slice(index + 1).find((l) => !l.locked);

  async function markComplete(lesson: TreeLesson) {
    setActionError("");
    setBusy(true);
    try {
      await completeLesson(lesson.id);
      onProgress();
      if (next) setSelectedId(next.id);
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="learn">
      <nav className="outline" aria-label="Course outline">
        {tree.modules.map((module) => (
          <div key={module.id} className="outline-module">
            <h3>{module.title}</h3>
            {module.chapters.map((chapter) => (
              <div key={chapter.id} className="outline-chapter">
                <div className="chapter-title">{chapter.title}</div>
                {chapter.lessons.map((lesson) => (
                  <button
                    key={lesson.id}
                    className="lesson-row"
                    aria-current={selected?.id === lesson.id}
                    disabled={lesson.locked}
                    onClick={() => setSelectedId(lesson.id)}
                    title={lesson.locked ? "Enroll to open this lesson" : undefined}
                  >
                    <span
                      className={lesson.completed ? "tick done" : lesson.locked ? "tick locked" : "tick"}
                      aria-hidden="true"
                    >
                      {lesson.completed ? "✓" : ""}
                    </span>
                    <span>{lesson.title}</span>
                    <span className="dur">
                      {lesson.locked ? "locked" : lesson.is_preview && !tree.can_access_content ? "preview" : lesson.duration_minutes ? `${lesson.duration_minutes}m` : ""}
                    </span>
                  </button>
                ))}
              </div>
            ))}
          </div>
        ))}
      </nav>

      <article className="viewer">
        {!selected ? (
          <div className="empty">
            <strong>Enroll to start learning</strong>
            Preview lessons are open to everyone. The rest unlock after you enroll.
          </div>
        ) : (
          <>
            <header className="viewer-head">
              <div>
                <div className="eyebrow">
                  Lesson {index + 1} of {lessons.length}
                </div>
                <h2>{selected.title}</h2>
                {selected.summary && <p className="lede">{selected.summary}</p>}
              </div>
              <div className="row">
                {canTrack && !selected.completed && (
                  <button disabled={busy} onClick={() => markComplete(selected)}>
                    Mark as complete
                  </button>
                )}
                {selected.completed && <span className="status completed">Completed</span>}
                {next && (
                  <button className="secondary" onClick={() => setSelectedId(next.id)}>
                    Next lesson
                  </button>
                )}
              </div>
            </header>
            {actionError && <p className="error">{actionError}</p>}
            {selected.contents.length === 0 && <p className="hint">This lesson has no material yet.</p>}
            {selected.contents.map((item) => (
              <ContentBlock key={item.id} item={item} lessonId={selected.id} track={canTrack} />
            ))}
          </>
        )}
      </article>
    </div>
  );
}

function ContentBlock({ item, lessonId, track }: { item: ContentItem; lessonId: number; track: boolean }) {
  const lastSaved = useRef(0);

  const savePosition = (seconds: number) => {
    if (!track || Math.abs(seconds - lastSaved.current) < 10) return;
    lastSaved.current = seconds;
    saveLessonPosition(lessonId, Math.floor(seconds)).catch(() => undefined);
  };

  return (
    <section className="content-block">
      <h3>
        <span className="chip">{KIND_LABEL[item.kind]}</span>
        {item.title}
      </h3>
      {item.kind === "video" && item.file && (
        <video
          controls
          preload="metadata"
          src={item.file}
          onPause={(e) => savePosition(e.currentTarget.currentTime)}
        />
      )}
      {item.kind === "video" && !item.file && item.url && (
        <a className="button secondary" href={item.url} target="_blank" rel="noreferrer">
          Watch video
        </a>
      )}
      {item.kind === "pdf" && item.file && <iframe src={item.file} title={item.title} />}
      {(item.kind === "ppt" || item.kind === "doc") && item.file && (
        <a className="button secondary" href={item.file} target="_blank" rel="noreferrer">
          Download {KIND_LABEL[item.kind].toLowerCase()}
        </a>
      )}
      {item.kind === "link" && (
        <a className="button secondary" href={item.url} target="_blank" rel="noreferrer">
          Open link
        </a>
      )}
      {item.kind === "text" && <div className="text">{item.text}</div>}
    </section>
  );
}
