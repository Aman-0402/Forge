import type { AttemptStatus, ExamPhase, QuestionType } from "../api/exams";

export const TYPE_LABEL: Record<QuestionType, string> = {
  mcq_single: "One answer",
  mcq_multi: "Several answers",
  true_false: "True / false",
  subjective: "Written",
};

export const PHASE_LABEL: Record<ExamPhase, string> = {
  draft: "Draft",
  scheduled: "Scheduled",
  upcoming: "Upcoming",
  live: "Open now",
  ended: "Window ended",
  closed: "Closed",
  archived: "Archived",
};

export const PHASE_CLASS: Record<ExamPhase, string> = {
  draft: "draft",
  scheduled: "pending_approval",
  upcoming: "pending_approval",
  live: "published",
  ended: "archived",
  closed: "archived",
  archived: "archived",
};

export const ATTEMPT_LABEL: Record<AttemptStatus, string> = {
  in_progress: "In progress",
  grading: "Awaiting grading",
  graded: "Graded",
};

export function formatDuration(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const mm = String(m).padStart(2, "0");
  const ss = String(sec).padStart(2, "0");
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}
