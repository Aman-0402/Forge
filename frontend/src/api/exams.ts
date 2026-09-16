import { api } from "./client";
import { cleanQuery, type Paginated, type Query } from "./types";

export type QuestionType = "mcq_single" | "mcq_multi" | "true_false" | "subjective";
export type Difficulty = "easy" | "medium" | "hard";
export type ExamStatus = "draft" | "scheduled" | "closed" | "archived";
export type ExamPhase = ExamStatus | "upcoming" | "live" | "ended";
export type AttemptStatus = "in_progress" | "grading" | "graded";

export type Bank = {
  id: number;
  title: string;
  description: string;
  owner: number;
  owner_name: string;
  course: number | null;
  is_shared: boolean;
  question_count: number;
  created_at: string;
};

export type OptionInput = { text: string; is_correct: boolean };

export type Question = {
  id: number;
  bank: number;
  type: QuestionType;
  text: string;
  marks: string;
  negative_marks: string;
  difficulty: Difficulty;
  explanation: string;
  tags: string[];
  is_active: boolean;
  options: (OptionInput & { id: number; order: number })[];
  used_in_exams: number | null;
};

export type QuestionInput = {
  type: QuestionType;
  text: string;
  marks: string;
  negative_marks: string;
  difficulty: Difficulty;
  explanation: string;
  tags: string[];
  options: OptionInput[];
};

export type Exam = {
  id: number;
  title: string;
  description: string;
  course: number | null;
  course_title: string | null;
  created_by: number;
  starts_at: string;
  ends_at: string;
  duration_minutes: number;
  pass_marks: string | null;
  shuffle_questions: boolean;
  shuffle_options: boolean;
  max_attempts: number;
  show_result_immediately: boolean;
  reveal_answers: boolean;
  integrity_tracking: boolean;
  results_released_at: string | null;
  status: ExamStatus;
  phase: ExamPhase;
  allowed_students?: number[];
  total_marks: string;
  question_count: number;
  attempt_count?: number | null;
  my_attempts?: { used: number; max: number; in_progress_id: number | null; can_start: boolean };
  can_manage: boolean;
};

export type ExamInput = Partial<
  Pick<
    Exam,
    | "title"
    | "description"
    | "course"
    | "starts_at"
    | "ends_at"
    | "duration_minutes"
    | "pass_marks"
    | "shuffle_questions"
    | "shuffle_options"
    | "max_attempts"
    | "show_result_immediately"
    | "reveal_answers"
    | "integrity_tracking"
  >
>;

export type ExamQuestionRow = { id: number; order: number; marks_override: string | null; marks: string; question: Question };

export type AttemptQuestion = {
  exam_question_id: number;
  index: number;
  type: QuestionType;
  text: string;
  marks: string;
  negative_marks: string;
  options: { id: number; text: string }[];
  answer: { selected_option_ids: number[]; text_answer: string };
};

export type LiveAttempt = {
  id: number;
  exam: { id: number; title: string; duration_minutes: number; ends_at: string; integrity_tracking: boolean };
  attempt_number: number;
  status: AttemptStatus;
  started_at: string;
  deadline_at: string;
  submitted_at: string | null;
  auto_submitted: boolean;
  seconds_remaining: number;
  questions: AttemptQuestion[];
};

export type ResultAnswer = {
  answer_id: number | null;
  exam_question_id: number;
  index: number;
  type: QuestionType;
  text: string;
  marks: string;
  options: { id: number; text: string; is_correct?: boolean; selected?: boolean }[];
  selected_option_ids: number[];
  text_answer: string;
  marks_awarded: string | null;
  is_correct: boolean | null;
  grader_feedback: string;
  correct_option_ids?: number[];
  explanation?: string;
};

export type AttemptResult = {
  id: number;
  exam: { id: number; title: string; pass_marks: string | null };
  attempt_number: number;
  status: AttemptStatus;
  started_at: string;
  submitted_at: string | null;
  auto_submitted: boolean;
  objective_score: string;
  subjective_score: string;
  total_score: string;
  total_marks: string;
  percentage: string;
  passed: boolean | null;
  answers: ResultAnswer[];
  student?: { id: number; email: string; name: string };
  integrity_events?: { kind: string; occurred_at: string; metadata: Record<string, unknown> }[];
};

export type AttemptRow = {
  id: number;
  student: number;
  student_detail: { id: number; email: string; name: string; roll_number: string | null };
  attempt_number: number;
  status: AttemptStatus;
  started_at: string;
  deadline_at: string;
  submitted_at: string | null;
  auto_submitted: boolean;
  total_score: string;
  percentage: string;
  passed: boolean | null;
  integrity_event_count: number;
};

export type ResultsSummary = {
  stats: {
    attempts: number;
    in_progress: number;
    awaiting_grading: number;
    graded: number;
    total_marks: string;
    average: string | null;
    highest: string | null;
    lowest: string | null;
    pass_rate: string | null;
  };
  rows: {
    attempt_id: number;
    email: string;
    name: string;
    roll_number: string | null;
    attempt_number: number;
    total_score: string;
    percentage: string;
    passed: boolean | null;
    submitted_at: string | null;
    auto_submitted: boolean;
  }[];
};

export type MyResult = {
  attempt_id: number;
  exam: { id: number; title: string };
  attempt_number: number;
  status: AttemptStatus;
  submitted_at: string | null;
  result_visible: boolean;
  total_score: string | null;
  percentage: string | null;
  passed: boolean | null;
};

// ---------- banks ----------

export const listBanks = async (q: Query = {}) =>
  (await api.get<Paginated<Bank>>("/question-banks/", { params: cleanQuery(q) })).data;
export const getBank = async (id: number) => (await api.get<Bank>(`/question-banks/${id}/`)).data;
export const createBank = async (body: Partial<Bank>) => (await api.post<Bank>("/question-banks/", body)).data;
export const updateBank = async (id: number, body: Partial<Bank>) =>
  (await api.patch<Bank>(`/question-banks/${id}/`, body)).data;
export const deleteBank = async (id: number) => {
  await api.delete(`/question-banks/${id}/`);
};
export const listQuestions = async (bankId: number, q: Query = {}) =>
  (await api.get<Paginated<Question>>(`/question-banks/${bankId}/questions/`, { params: cleanQuery(q) })).data;
export const createQuestion = async (bankId: number, body: QuestionInput) =>
  (await api.post<Question>(`/question-banks/${bankId}/questions/`, body)).data;
export const updateQuestion = async (id: number, body: Partial<QuestionInput> & { is_active?: boolean }) =>
  (await api.patch<Question>(`/questions/${id}/`, body)).data;
export const deleteQuestion = async (id: number) => {
  await api.delete(`/questions/${id}/`);
};
export const importQuestions = async (bankId: number, questions: unknown[]) =>
  (await api.post<{ created: number }>(`/question-banks/${bankId}/import/`, { questions })).data;

// ---------- exams ----------

export const listExams = async (q: Query = {}) =>
  (await api.get<Paginated<Exam>>("/exams/", { params: cleanQuery(q) })).data;
export const getExam = async (id: number) => (await api.get<Exam>(`/exams/${id}/`)).data;
export const createExam = async (body: ExamInput) => (await api.post<Exam>("/exams/", body)).data;
export const updateExam = async (id: number, body: ExamInput) => (await api.patch<Exam>(`/exams/${id}/`, body)).data;
export const deleteExam = async (id: number) => {
  await api.delete(`/exams/${id}/`);
};
export const examAction = async (
  id: number,
  action: "schedule" | "unschedule" | "close" | "release-results",
) => (await api.post<Exam>(`/exams/${id}/${action}/`)).data;
export const extendExam = async (id: number, ends_at: string) =>
  (await api.post<Exam>(`/exams/${id}/extend/`, { ends_at })).data;
export const examQuestions = async (id: number) =>
  (await api.get<ExamQuestionRow[]>(`/exams/${id}/questions/`)).data;
export const addExamQuestions = async (
  id: number,
  body: { question_ids?: number[]; bank?: number; count?: number; difficulty?: string; type?: string },
) => (await api.post<ExamQuestionRow[]>(`/exams/${id}/questions/`, body)).data;
export const updateExamQuestion = async (id: number, rowId: number, body: { marks_override: string | null }) =>
  (await api.patch<ExamQuestionRow>(`/exams/${id}/questions/${rowId}/`, body)).data;
export const removeExamQuestion = async (id: number, rowId: number) => {
  await api.delete(`/exams/${id}/questions/${rowId}/`);
};

// ---------- attempts ----------

export const startExam = async (id: number) => (await api.post<LiveAttempt>(`/exams/${id}/start/`)).data;
export const getAttempt = async (id: number) => (await api.get<LiveAttempt>(`/attempts/${id}/`)).data;
export const saveAnswer = async (
  attemptId: number,
  examQuestionId: number,
  body: { selected_option_ids?: number[]; text_answer?: string },
) =>
  (
    await api.put<{ seconds_remaining: number }>(
      `/attempts/${attemptId}/answers/${examQuestionId}/`,
      body,
    )
  ).data;
export const submitAttempt = async (id: number) => (await api.post<LiveAttempt>(`/attempts/${id}/submit/`)).data;
export const reportIntegrity = async (id: number, kind: string, metadata: Record<string, unknown> = {}) => {
  await api.post(`/attempts/${id}/integrity-events/`, { kind, metadata });
};

// ---------- grading & results ----------

export const examAttempts = async (id: number, q: Query = {}) =>
  (await api.get<Paginated<AttemptRow>>(`/exams/${id}/attempts/`, { params: cleanQuery(q) })).data;
export const reviewAttempt = async (id: number) => (await api.get<AttemptResult>(`/attempts/${id}/review/`)).data;
export const gradeAnswer = async (answerId: number, marks_awarded: string, grader_feedback: string) =>
  (await api.patch(`/answers/${answerId}/grade/`, { marks_awarded, grader_feedback })).data;
export const attemptResult = async (id: number) => (await api.get<AttemptResult>(`/attempts/${id}/result/`)).data;
export const examResults = async (id: number) => (await api.get<ResultsSummary>(`/exams/${id}/results/`)).data;
export const myResults = async (q: Query = {}) =>
  (await api.get<Paginated<MyResult>>("/me/results/", { params: cleanQuery(q) })).data;

export async function downloadResultsCsv(id: number, filename: string) {
  const res = await api.get(`/exams/${id}/results/export/`, { responseType: "blob" });
  const url = URL.createObjectURL(res.data as Blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
