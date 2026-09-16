import { api } from "./client";
import { cleanQuery, type Paginated, type Query } from "./types";

export type Verdict =
  | "accepted"
  | "partial"
  | "wrong_answer"
  | "time_limit"
  | "memory_limit"
  | "runtime_error"
  | "compile_error"
  | "internal_error";

export type Language = {
  id: number;
  name: string;
  slug: string;
  version: string;
  judge0_id: number;
  editor_mode: string;
  default_template: string;
  is_enabled: boolean;
};

export type SampleCase = { input: string; expected_output: string; explanation: string };

export type Problem = {
  id: number;
  title: string;
  slug: string;
  statement: string;
  input_format: string;
  output_format: string;
  constraints: string;
  difficulty: "easy" | "medium" | "hard";
  tags: string[];
  time_limit_seconds: string;
  memory_limit_kb: number;
  max_score: number;
  allow_partial: boolean;
  course: number | null;
  course_title: string | null;
  created_by: number;
  status: "draft" | "published" | "archived";
  allowed_languages: number[];
  languages: Language[];
  visible_from: string | null;
  visible_until: string | null;
  sample_cases: SampleCase[];
  test_case_count: number;
  can_manage: boolean;
  my_status: { attempts: number; best_score: number; solved: boolean } | null;
};

export type ProblemInput = Partial<
  Pick<
    Problem,
    | "title"
    | "statement"
    | "input_format"
    | "output_format"
    | "constraints"
    | "difficulty"
    | "tags"
    | "time_limit_seconds"
    | "memory_limit_kb"
    | "max_score"
    | "allow_partial"
    | "course"
    | "allowed_languages"
    | "visible_from"
    | "visible_until"
  >
>;

export type TestCase = {
  id: number;
  problem: number;
  input: string;
  expected_output: string;
  is_sample: boolean;
  is_hidden: boolean;
  weight: number;
  order: number;
  explanation: string;
};

export type RunResult = {
  mode: "samples" | "custom";
  compile_output: string;
  results: {
    index: number;
    input: string;
    expected_output: string | null;
    stdout: string;
    stderr: string;
    status: string;
    verdict: Verdict | null;
    passed: boolean | null;
    time_seconds: number | null;
    memory_kb: number | null;
  }[];
};

export type SubmissionRow = {
  id: number;
  problem: number;
  problem_title: string;
  student: number;
  student_name: string;
  language: number;
  language_name: string;
  status: "queued" | "running" | "done" | "error";
  verdict: Verdict | "";
  score: number;
  passed_count: number;
  total_count: number;
  max_time_seconds: string | null;
  max_memory_kb: number | null;
  submitted_at: string;
  judged_at: string | null;
};

export type SubmissionDetail = SubmissionRow & {
  source_code: string;
  compile_output: string;
  results: {
    index: number;
    verdict: Verdict;
    passed: boolean;
    time_seconds: string | null;
    memory_kb: number | null;
    hidden: boolean;
    is_sample: boolean;
    input?: string;
    expected_output?: string;
    stdout?: string;
    stderr?: string;
  }[];
};

export type LeaderboardRow = {
  rank: number;
  student_id: number;
  name: string;
  best_score: number;
  attempts: number;
  reached_at: string;
};

export const listLanguages = async () => (await api.get<Language[]>("/languages/")).data;

export const listProblems = async (q: Query = {}) =>
  (await api.get<Paginated<Problem>>("/problems/", { params: cleanQuery(q) })).data;
export const getProblem = async (id: number) => (await api.get<Problem>(`/problems/${id}/`)).data;
export const createProblem = async (body: ProblemInput) => (await api.post<Problem>("/problems/", body)).data;
export const updateProblem = async (id: number, body: ProblemInput) =>
  (await api.patch<Problem>(`/problems/${id}/`, body)).data;
export const deleteProblem = async (id: number) => {
  await api.delete(`/problems/${id}/`);
};
export const problemAction = async (id: number, action: "publish" | "unpublish" | "archive") =>
  (await api.post<Problem>(`/problems/${id}/${action}/`)).data;
export const rejudgeProblem = async (id: number) =>
  (await api.post<{ rejudged: number; failed: number }>(`/problems/${id}/rejudge/`)).data;

export const listTestCases = async (problemId: number) =>
  (await api.get<TestCase[]>(`/problems/${problemId}/testcases/`)).data;
export const createTestCase = async (problemId: number, body: Partial<TestCase>) =>
  (await api.post<TestCase>(`/problems/${problemId}/testcases/`, body)).data;
export const updateTestCase = async (id: number, body: Partial<TestCase>) =>
  (await api.patch<TestCase>(`/testcases/${id}/`, body)).data;
export const deleteTestCase = async (id: number) => {
  await api.delete(`/testcases/${id}/`);
};
export const importTestCases = async (problemId: number, cases: unknown[]) =>
  (await api.post<{ created: number }>(`/problems/${problemId}/testcases/import/`, { cases })).data;

export const runCode = async (problemId: number, body: { language: number; source_code: string; stdin?: string }) =>
  (await api.post<RunResult>(`/problems/${problemId}/run/`, body)).data;
export const submitCode = async (problemId: number, body: { language: number; source_code: string }) =>
  (await api.post<SubmissionDetail>(`/problems/${problemId}/submit/`, body)).data;
export const listProblemSubmissions = async (problemId: number, q: Query = {}) =>
  (await api.get<Paginated<SubmissionRow>>(`/problems/${problemId}/submissions/`, { params: cleanQuery(q) })).data;
export const getSubmission = async (id: number) =>
  (await api.get<SubmissionDetail>(`/code-submissions/${id}/`)).data;
export const getLeaderboard = async (problemId: number) =>
  (await api.get<LeaderboardRow[]>(`/problems/${problemId}/leaderboard/`)).data;
export const myCodingSummary = async () =>
  (
    await api.get<{ solved: number; attempted: number; submissions: number; recent: SubmissionRow[] }>(
      "/me/coding/summary/",
    )
  ).data;
