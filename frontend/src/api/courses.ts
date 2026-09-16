import { api } from "./client";
import { cleanQuery, type Paginated, type Query } from "./types";

export type CourseStatus = "draft" | "pending_approval" | "published" | "archived";
export type Level = "beginner" | "intermediate" | "advanced";
export type EnrollmentMode = "manual" | "open" | "auto_department" | "auto_batch";
export type ContentKind = "video" | "pdf" | "ppt" | "doc" | "link" | "text";

export type UserBrief = { id: number; email: string; name: string };
export type StudentBrief = UserBrief & { roll_number: string | null; batch: string | null };

export type Category = { id: number; name: string; slug: string; kind: string; parent: number | null };

export type Course = {
  id: number;
  title: string;
  slug: string;
  code: string;
  description: string;
  thumbnail: string | null;
  instructor: number;
  instructor_detail: UserBrief;
  co_instructors: number[];
  co_instructors_detail: UserBrief[];
  categories: number[];
  categories_detail: { id: number; name: string; slug: string }[];
  department: number | null;
  department_code: string | null;
  level: Level;
  status: CourseStatus;
  rejection_reason: string;
  submitted_at: string | null;
  approved_at: string | null;
  enrollment_mode: EnrollmentMode;
  auto_enroll_batch: string;
  start_date: string | null;
  end_date: string | null;
  lesson_count: number;
  enrollment_count: number;
  is_enrolled: boolean;
  my_progress: number | null;
  can_manage: boolean;
  created_at: string;
  updated_at: string;
};

export type CourseInput = Partial<
  Pick<
    Course,
    | "title"
    | "code"
    | "description"
    | "instructor"
    | "co_instructors"
    | "categories"
    | "department"
    | "level"
    | "enrollment_mode"
    | "auto_enroll_batch"
    | "start_date"
    | "end_date"
  >
>;

export type ContentItem = {
  id: number;
  lesson: number;
  kind: ContentKind;
  title: string;
  file: string | null;
  url: string;
  text: string;
  order: number;
};

export type TreeLesson = {
  id: number;
  title: string;
  summary: string;
  order: number;
  duration_minutes: number | null;
  is_preview: boolean;
  locked: boolean;
  completed: boolean;
  contents: ContentItem[];
};

export type TreeChapter = {
  id: number;
  title: string;
  description: string;
  order: number;
  lessons: TreeLesson[];
};

export type TreeModule = {
  id: number;
  title: string;
  description: string;
  order: number;
  chapters: TreeChapter[];
};

export type CourseTree = {
  course: number;
  title: string;
  can_access_content: boolean;
  is_enrolled: boolean;
  progress_percent: number | null;
  lesson_count: number;
  completed_lesson_ids: number[];
  modules: TreeModule[];
};

export type Enrollment = {
  id: number;
  course: number;
  course_detail: {
    id: number;
    title: string;
    slug: string;
    code: string;
    thumbnail: string | null;
    level: Level;
    status: CourseStatus;
    instructor_name: string;
  };
  student: number;
  student_detail: StudentBrief;
  status: "active" | "completed" | "dropped";
  source: "self" | "manual" | "auto";
  enrolled_at: string;
  completed_at: string | null;
  progress_percent: number;
};

export type ProgressRow = {
  id: number;
  student: number;
  student_detail: StudentBrief;
  status: Enrollment["status"];
  progress_percent: number;
  completed_lessons: number;
  total_lessons: number;
  enrolled_at: string;
  completed_at: string | null;
  last_activity: string | null;
};

export type Assignment = {
  id: number;
  course: number;
  title: string;
  description: string;
  attachment: string | null;
  due_at: string | null;
  max_marks: string;
  allow_late: boolean;
  created_by: number | null;
  submission_count: number | null;
  graded_count: number | null;
  my_submission: {
    id: number;
    submitted_at: string;
    is_late: boolean;
    graded: boolean;
    marks: string | null;
  } | null;
  created_at: string;
};

export type Submission = {
  id: number;
  assignment: number;
  assignment_title: string;
  student: number;
  student_detail: StudentBrief;
  file: string | null;
  text: string;
  submitted_at: string;
  is_late: boolean;
  marks: string | null;
  max_marks: string;
  feedback: string;
  graded_by: number | null;
  graded_at: string | null;
};

type Level3 = "modules" | "chapters" | "lessons" | "content";
const PARENT: Record<Level3, string> = {
  modules: "courses",
  chapters: "modules",
  lessons: "chapters",
  content: "lessons",
};

// ---------- catalog ----------

export const listCourses = async (q: Query) =>
  (await api.get<Paginated<Course>>("/courses/", { params: cleanQuery(q) })).data;

export const getCourse = async (id: number) => (await api.get<Course>(`/courses/${id}/`)).data;

export const createCourse = async (body: CourseInput) =>
  (await api.post<Course>("/courses/", body)).data;

export const updateCourse = async (id: number, body: CourseInput) =>
  (await api.patch<Course>(`/courses/${id}/`, body)).data;

export const deleteCourse = async (id: number) => {
  await api.delete(`/courses/${id}/`);
};

export const courseAction = async (
  id: number,
  action: "submit-for-approval" | "approve" | "reject" | "archive",
  body?: { reason: string },
) => (await api.post<Course>(`/courses/${id}/${action}/`, body)).data;

export const listCategories = async () =>
  (await api.get<Paginated<Category>>("/categories/", { params: { page_size: 100 } })).data
    .results;

export const createCategory = async (body: { name: string; kind: string }) =>
  (await api.post<Category>("/categories/", body)).data;

// ---------- structure ----------

export const getTree = async (id: number) =>
  (await api.get<CourseTree>(`/courses/${id}/tree/`)).data;

export const createNode = async (level: Level3, parentId: number, body: object | FormData) =>
  (await api.post(`/${PARENT[level]}/${parentId}/${level}/`, body)).data;

export const updateNode = async (level: Level3, id: number, body: object) =>
  (await api.patch(`/${level}/${id}/`, body)).data;

export const deleteNode = async (level: Level3, id: number) => {
  await api.delete(`/${level}/${id}/`);
};

export const reorderNodes = async (level: Level3, parentId: number, ids: number[]) => {
  await api.post(`/${PARENT[level]}/${parentId}/${level}/reorder/`, { ids });
};

// ---------- enrollment & progress ----------

export const enroll = async (courseId: number) =>
  (await api.post<Enrollment>(`/courses/${courseId}/enroll/`)).data;

export const dropCourse = async (courseId: number) =>
  (await api.post<Enrollment>(`/courses/${courseId}/drop/`)).data;

export const myEnrollments = async (q: Query = {}) =>
  (await api.get<Paginated<Enrollment>>("/me/enrollments/", { params: cleanQuery(q) })).data;

export const courseEnrollments = async (courseId: number, q: Query) =>
  (
    await api.get<Paginated<Enrollment>>(`/courses/${courseId}/enrollments/`, {
      params: cleanQuery(q),
    })
  ).data;

export const bulkEnroll = async (
  courseId: number,
  body: { student_ids?: number[]; batch?: string; department?: number | null },
) =>
  (
    await api.post<{ enrolled: number[]; already_enrolled: number[]; invalid: number[] }>(
      `/courses/${courseId}/enrollments/`,
      body,
    )
  ).data;

export const removeEnrollment = async (id: number) => {
  await api.delete(`/enrollments/${id}/`);
};

export const courseProgress = async (courseId: number, q: Query) =>
  (
    await api.get<Paginated<ProgressRow>>(`/courses/${courseId}/progress/`, {
      params: cleanQuery(q),
    })
  ).data;

export const completeLesson = async (lessonId: number) =>
  (await api.post<Enrollment>(`/lessons/${lessonId}/complete/`)).data;

export const saveLessonPosition = async (lessonId: number, seconds: number) => {
  await api.post(`/lessons/${lessonId}/position/`, { seconds });
};

// ---------- assignments ----------

export const listAssignments = async (courseId: number) =>
  (await api.get<Assignment[]>(`/courses/${courseId}/assignments/`)).data;

export const getAssignment = async (id: number) =>
  (await api.get<Assignment>(`/assignments/${id}/`)).data;

export const createAssignment = async (courseId: number, body: FormData) =>
  (await api.post<Assignment>(`/courses/${courseId}/assignments/`, body)).data;

export const deleteAssignment = async (id: number) => {
  await api.delete(`/assignments/${id}/`);
};

export const submitAssignment = async (id: number, body: FormData) =>
  (await api.post<Submission>(`/assignments/${id}/submit/`, body)).data;

export const listSubmissions = async (assignmentId: number, q: Query = {}) =>
  (
    await api.get<Paginated<Submission>>(`/assignments/${assignmentId}/submissions/`, {
      params: cleanQuery(q),
    })
  ).data;

export const gradeSubmission = async (id: number, marks: string, feedback: string) =>
  (await api.post<Submission>(`/submissions/${id}/grade/`, { marks, feedback })).data;
