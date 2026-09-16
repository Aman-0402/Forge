# Phase 2 — Courses Module

**Goal:** Faculty build courses (modules → chapters → lessons → content), categorize them, enroll students manually or automatically, create assignments; students consume content, submit assignments, and their progress is tracked. Admin approves courses.

**Maps to source doc:** §6 Module 1, Week 2.

**Depends on:** Phase 1.

**Estimated effort:** 3–4 days.

## Data model (`apps/courses`)

| Model | Fields |
|---|---|
| `Category` | `name`, `slug` (unique), `kind` (enum: department/subject/level), `parent` FK self null |
| `Course` | `title`, `slug` (unique), `code`, `description`, `thumbnail` (image), `instructor` FK User (faculty), `co_instructors` M2M, `categories` M2M, `department` FK null, `level` (enum beginner/intermediate/advanced), `status` (enum draft/pending_approval/published/archived), `approved_by` FK null, `approved_at`, `enrollment_mode` (enum manual/open/auto_department/auto_batch), `start_date`, `end_date`, `is_active`, timestamps |
| `Module` | `course` FK, `title`, `description`, `order` (int) |
| `Chapter` | `module` FK, `title`, `description`, `order` |
| `Lesson` | `chapter` FK, `title`, `summary`, `order`, `duration_minutes`, `is_preview` |
| `ContentItem` | `lesson` FK, `kind` (enum video/pdf/ppt/doc/link/text), `title`, `file` (FileField, validated ext/size), `url`, `text` (rich text/markdown), `order` |
| `Enrollment` | `course` FK, `student` FK, `status` (enum active/completed/dropped), `enrolled_by` FK null (admin/faculty/self), `enrolled_at`, `completed_at`, `progress_percent` (cached) — unique (course, student) |
| `LessonProgress` | `enrollment` FK, `lesson` FK, `completed_at`, `last_position_seconds` (video) — unique (enrollment, lesson) |
| `Assignment` | `course` FK, `title`, `description`, `attachment`, `due_at`, `max_marks`, `allow_late`, `created_by` FK, timestamps |
| `AssignmentSubmission` | `assignment` FK, `student` FK, `file`, `text`, `submitted_at`, `is_late`, `marks`, `feedback`, `graded_by` FK null, `graded_at` — unique (assignment, student) |
| `Certificate` | `enrollment` O2O, `serial` (uuid), `issued_at`, `pdf` (file) — **optional, last** |

## Business rules (services.py)
- Faculty can edit only courses where they are instructor/co-instructor. Admin edits any.
- Publish flow: faculty sets `pending_approval` → admin `approve` → `published`. Admin may publish directly.
- Students see only `published` courses. Content of unenrolled course: only `is_preview` lessons.
- Enrollment: `manual` (faculty/admin adds), `open` (student self-enrolls), `auto_department` / `auto_batch` (signal on user create/update or command `sync_auto_enrollments`).
- Progress: marking lesson complete recomputes `Enrollment.progress_percent`; 100% sets `status=completed`, `completed_at`, triggers optional certificate + notification.
- Assignment submission after `due_at` allowed only if `allow_late`; flagged `is_late`.
- Grading by instructor/co-instructor/admin; notifies student.
- File validation: allowed ext per `kind`, max size from settings (`MAX_UPLOAD_MB`).

## API

| Method | Path | Role |
|---|---|---|
| CRUD | `categories/` | admin write, all read |
| GET/POST | `courses/` | faculty/admin create; list filtered by role (student→published+enrolled flag) |
| GET/PATCH/DELETE | `courses/{id}/` | owner faculty / admin |
| POST | `courses/{id}/submit-for-approval/` · `approve/` · `reject/` · `archive/` | faculty / admin |
| CRUD | `courses/{id}/modules/` · `modules/{id}/chapters/` · `chapters/{id}/lessons/` · `lessons/{id}/content/` | owner faculty / admin |
| POST | `.../reorder/` on modules/chapters/lessons/content | owner faculty / admin |
| GET | `courses/{id}/tree/` | enrolled student / owner / admin — full nested structure (one query set with prefetch) |
| POST | `courses/{id}/enroll/` | student (open mode) |
| GET/POST/DELETE | `courses/{id}/enrollments/` · `enrollments/{id}/` | owner faculty / admin; bulk add by user ids or batch |
| GET | `me/enrollments/` | student |
| POST | `lessons/{id}/complete/` · `lessons/{id}/position/` | enrolled student |
| GET | `courses/{id}/progress/` (all students) · `courses/{id}/progress/me/` | faculty/admin · student |
| CRUD | `courses/{id}/assignments/` | owner faculty / admin write; enrolled read |
| GET/POST | `assignments/{id}/submissions/` | student submit (own); faculty list |
| GET/PATCH | `submissions/{id}/` · `POST submissions/{id}/grade/` | student own read; faculty grade |
| GET | `enrollments/{id}/certificate/` | student own / faculty / admin (optional) |

## Checklist
- [ ] Models, migrations, factories.
- [ ] Permissions: `IsCourseInstructorOrAdmin`, `IsEnrolledStudent`.
- [ ] Course CRUD + approval flow + tests.
- [ ] Structure CRUD (module/chapter/lesson/content) + reorder + tree endpoint + tests.
- [ ] File upload validation + tests (bad ext, too large).
- [ ] Enrollment: manual, open, auto (signal + management command) + tests.
- [ ] Progress tracking + recompute + completion + tests.
- [ ] Assignments + submissions + grading + late logic + notifications + tests.
- [ ] Audit log on course approve/publish, enrollment changes, grading.
- [ ] Optional: certificate PDF (reportlab) — do last or defer to Phase 5.
- [ ] Frontend (minimal): faculty `/faculty/courses` list+create, course editor (nested structure with add/reorder), enrollments page; student `/student/courses`, course viewer (tree + content + mark complete), assignments submit; admin approval queue.
- [ ] Update `agent.md`; commit + push per feature.

## Definition of done
- Faculty creates course with 1 module/1 chapter/2 lessons and uploads a PDF; submits for approval; admin approves.
- Student self-enrolls (open), completes both lessons, progress shows 100%, enrollment marked completed.
- Student submits assignment; faculty grades; student receives notification.
- Tests green, pushed.
