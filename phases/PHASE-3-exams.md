# Phase 3 — Exam Module

**Goal:** Faculty build question banks (MCQ, true/false, subjective), schedule exams with a window and duration, students attempt inside the window with randomized questions and a server-enforced timer, objective questions auto-grade, subjective ones go through a manual grading queue, and results/scorecards are released to students.

**Maps to source doc:** §7 Module 2, Week 3.

**Depends on:** Phase 2 (exam may be attached to a course; enrollment gates eligibility).

**Estimated effort:** 4 days. This is the most correctness-sensitive module.

## Data model (`apps/exams`)

| Model | Fields |
|---|---|
| `QuestionBank` | `title`, `description`, `owner` FK faculty, `course` FK null, `category` FK null, `is_shared` (other faculty may use), timestamps |
| `Question` | `bank` FK, `type` (enum mcq_single/mcq_multi/true_false/subjective), `text` (markdown), `image`, `marks` (decimal), `negative_marks` (decimal, default 0), `difficulty` (enum easy/medium/hard), `explanation`, `tags` (array/JSON), `is_active`, timestamps |
| `Option` | `question` FK, `text`, `image`, `is_correct`, `order` — for objective types only |
| `Exam` | `title`, `description`, `course` FK null, `created_by` FK, `starts_at`, `ends_at` (window), `duration_minutes`, `total_marks` (computed), `pass_marks`, `shuffle_questions`, `shuffle_options`, `max_attempts` (default 1), `show_result_immediately` (objective-only exams), `results_released_at` (null until faculty releases), `status` (enum draft/scheduled/live/closed/archived), `integrity_tracking` (bool), `allowed_students` M2M null (empty = all enrolled in course, or all students if no course), timestamps |
| `ExamQuestion` | `exam` FK, `question` FK, `order`, `marks_override` null — unique (exam, question) |
| `Attempt` | `exam` FK, `student` FK, `attempt_number`, `started_at`, `deadline_at` (= started_at + duration, capped at exam.ends_at), `submitted_at` null, `auto_submitted` (bool), `status` (enum in_progress/submitted/grading/graded), `question_order` (JSON list of exam_question ids), `option_orders` (JSON {exam_question_id: [option ids]}), `objective_score`, `subjective_score`, `total_score`, `percentage`, `passed` null, `ip`, `user_agent` — unique (exam, student, attempt_number) |
| `Answer` | `attempt` FK, `exam_question` FK, `selected_options` M2M Option, `text_answer`, `is_correct` null, `marks_awarded` null, `graded_by` FK null, `grader_feedback`, `answered_at`, `updated_at` — unique (attempt, exam_question) |
| `IntegrityEvent` | `attempt` FK, `kind` (enum tab_switch/fullscreen_exit/window_blur/copy/paste/devtools), `occurred_at`, `metadata` JSON |

## Business rules (services.py)
- **Eligibility to start:** exam `status in (scheduled, live)`, `now` within `[starts_at, ends_at)`, student in `allowed_students` or enrolled in `course`, attempts used `< max_attempts`.
- **Start:** create `Attempt`; compute `deadline_at = min(started_at + duration, ends_at)`; generate `question_order` (shuffled if flagged) and `option_orders` per question; persist. Return questions in that order **without** `is_correct` or `explanation`.
- **Resume:** `GET attempts/{id}/` for in-progress attempt returns same order and saved answers plus `seconds_remaining`.
- **Answer save:** upsert `Answer`; reject if `now > deadline_at + GRACE_SECONDS` (settings, default 10) or attempt not in progress. Validate options belong to question; `mcq_single`/`true_false` accept exactly one.
- **Submit:** set `submitted_at`, run objective grading synchronously, set `status = graded` if no subjective questions else `grading`. Notify student. Audit.
- **Auto-submit:** any read of an in-progress attempt past deadline submits it first (lazy). Plus management command `sweep_overdue_attempts` (cron every minute in prod) to close abandoned attempts.
- **Objective grading:** `mcq_single`/`true_false`: full marks if selected == correct, else `-negative_marks`. `mcq_multi`: full marks only if set equality (partial marking deferred). Store `is_correct`, `marks_awarded`.
- **Subjective grading:** faculty (exam creator, course instructor, or admin) sets `marks_awarded ≤ marks` and feedback per answer; when all subjective answers graded → recompute totals, `status = graded`.
- **Result visibility:** student sees score only if `show_result_immediately` (and exam fully objective) or `results_released_at` set. Correct answers/explanations visible only after release and only if exam setting allows (`reveal_answers`, add to Exam).
- **Exam edits locked** once any attempt exists (except `ends_at` extension and release fields).
- **Status transitions:** draft → scheduled (validate ≥1 question, window valid) → live (auto by time or manual) → closed (auto when `ends_at` passes) → archived.
- **Integrity events:** frontend posts events; backend stores; faculty sees count per attempt. No auto-fail (client to confirm).
- **Concurrency:** answer upsert uses `select_for_update` on attempt row; start uses `get_or_create` guarded by unique constraint.

## API

| Method | Path | Role |
|---|---|---|
| CRUD | `question-banks/` · `question-banks/{id}/questions/` · `questions/{id}/` | owner faculty / admin; shared banks readable by all faculty |
| POST | `question-banks/{id}/import/` | CSV/JSON bulk import of questions with options |
| CRUD | `exams/` · `exams/{id}/` | faculty/admin; student list = eligible exams with `my_attempts` summary |
| POST/DELETE | `exams/{id}/questions/` (bulk add by ids or random pick `{bank, count, difficulty}`) · `exams/{id}/questions/{eq_id}/` | owner / admin |
| POST | `exams/{id}/schedule/` · `close/` · `release-results/` · `extend/` | owner / admin |
| POST | `exams/{id}/start/` | eligible student |
| GET | `attempts/{id}/` | own student (in-progress view) / faculty / admin |
| PUT | `attempts/{id}/answers/{exam_question_id}/` | own student, before deadline |
| POST | `attempts/{id}/submit/` | own student |
| POST | `attempts/{id}/integrity-events/` | own student |
| GET | `exams/{id}/attempts/` | owner / admin — grading queue with filters `status=grading` |
| GET/PATCH | `attempts/{id}/grading/` (answers with full detail) · `PATCH answers/{id}/grade/` | owner / admin |
| GET | `attempts/{id}/result/` | own student (if released) / faculty / admin |
| GET | `exams/{id}/results/` · `exams/{id}/results/export/` (CSV) | owner / admin |
| GET | `me/results/` | student — performance history |

## Checklist
- [x] Models, migrations, factories, constraints (unique constraints in DB; `marks_awarded <= marks` enforced in the grading service).
- [x] Question bank CRUD + option validation (objective needs ≥2 options, ≥1 correct; single types exactly 1 correct) + import + tests.
- [x] Exam CRUD + question attach (manual + random pick) + status transitions + edit lock + tests.
- [x] Start attempt: eligibility matrix tests (outside window, not enrolled, max attempts, draft exam), randomization persisted, no answer leakage in payload (assert `is_correct` absent).
- [x] Answer upsert + deadline enforcement + validation + tests (time frozen with `freezegun` — add to dev deps).
- [x] Submit + objective grading + tests for every question type incl. negative marks.
- [x] Lazy auto-submit + `sweep_overdue_attempts` command + tests.
- [x] Subjective grading queue + totals recompute + tests.
- [x] Result visibility rules + release + export + tests.
- [x] Integrity events + tests.
- [x] Notifications: exam scheduled (to eligible students), results released. Audit: start, submit, grade, release.
- [x] Load sanity: `manage.py exam_load_check` — 200 students x 10 questions, 50 workers against dev runserver: 3980 answer saves + 199 submits, 0 application errors, 0 duplicate attempts, 1 connection refused by runserver backlog. p95 answer save 1.3 s on runserver (single process); production latency to be measured in Phase 5.
- [x] Frontend (minimal): faculty question bank editor, exam builder, grading queue, results table; student exam list, attempt screen with timer + navigation + auto-submit at 0, result page. Emit `tab_switch`/`fullscreen_exit` events via `visibilitychange`/`fullscreenchange`.
- [x] Update `agent.md`; commit + push per feature.

## Definition of done
- Faculty creates a bank with 5 MCQ + 1 subjective, schedules a 10-minute exam for a course.
- Enrolled student starts, answers, submits; objective score correct; attempt in `grading`.
- Faculty grades subjective; totals correct; releases results; student sees scorecard; unenrolled student gets 403 on start.
- Attempt left open past deadline is auto-submitted by sweep.
- Tests green, pushed.

## As built (differences from plan)
- Exam `status` stores draft / scheduled / closed / archived. "Upcoming", "live" and "ended" are derived from the window (`Exam.phase`), so no cron job flips statuses.
- Extra endpoints: `exams/{id}/unschedule/`, `exams/{id}/close/`, `exams/{id}/start/` (201 new, 200 resume), `attempts/{id}/review/` (staff), `answers/{id}/grade/`, `me/results/`.
- Answer path is `PUT attempts/{id}/answers/{exam_question_id}/`; grading is per answer.
- Question bank import is JSON only (CSV not built).
- Questions used by an attempted exam can only be deactivated, not edited; questions in any exam cannot be deleted.
- Exam edits after the first attempt are limited to title, description and `reveal_answers`; the window can still be extended.
- Objective grading: exact match gets full marks, empty gets 0, anything else gets `-negative_marks`. `mcq_multi` has no partial credit. Attempt totals are floored at 0.
- Unanswered written questions are auto-graded 0, so only real written answers enter the grading queue.
- Release is blocked while any attempt awaits grading.
- `show_result_immediately` only applies once an attempt is fully graded.
- Integrity events are recorded but never fail an attempt (policy to confirm with client).
- Answer grace window: `EXAM_GRACE_SECONDS` (10 s).
- Production needs `manage.py sweep_overdue_attempts` on a one-minute schedule (lazy auto-submit covers attempts that are touched again).
- Demo data: `manage.py seed_demo_exams` (after `seed_demo_courses`).