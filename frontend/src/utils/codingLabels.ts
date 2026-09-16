import type { Verdict } from "../api/coding";

export const VERDICT_LABEL: Record<Verdict, string> = {
  accepted: "Accepted",
  partial: "Partially correct",
  wrong_answer: "Wrong answer",
  time_limit: "Time limit exceeded",
  memory_limit: "Memory limit exceeded",
  runtime_error: "Runtime error",
  compile_error: "Compilation error",
  internal_error: "Judge error",
};

/** Maps a verdict onto the shared status chip colours. */
export const VERDICT_CLASS: Record<Verdict, string> = {
  accepted: "published",
  partial: "pending_approval",
  wrong_answer: "late",
  time_limit: "late",
  memory_limit: "late",
  runtime_error: "late",
  compile_error: "late",
  internal_error: "archived",
};

export const DIFFICULTY_LABEL = { easy: "Easy", medium: "Medium", hard: "Hard" } as const;
