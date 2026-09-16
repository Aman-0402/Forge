"""Concurrency sanity check for exam attempts against a running dev server.

Creates LOADTEST users and an exam, runs N students in parallel (start, answer every
question twice, submit), prints error counts and latency percentiles, then deletes
everything it created. DEBUG only.

    uv run python manage.py exam_load_check --students 200 --base-url http://localhost:8000
"""

import json
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.models import AuditLog
from apps.exams.models import Attempt, Exam, ExamQuestion, Option, Question, QuestionBank

User = get_user_model()
PREFIX = "loadtest-"


class Command(BaseCommand):
    help = "Run many concurrent exam attempts against a running dev server (DEBUG only)."

    def add_arguments(self, parser):
        parser.add_argument("--students", type=int, default=200)
        parser.add_argument("--questions", type=int, default=10)
        parser.add_argument("--workers", type=int, default=50)
        parser.add_argument("--base-url", default="http://localhost:8000")
        parser.add_argument("--keep", action="store_true", help="Do not delete created data")

    def handle(self, *args, **opts):
        if not settings.DEBUG:
            raise CommandError("exam_load_check only runs with DEBUG=True.")
        self.api = opts["base_url"].rstrip("/") + "/api/v1"
        exam, students = self._setup(opts["students"], opts["questions"])
        try:
            self._run(exam, students, opts["workers"])
        finally:
            if not opts["keep"]:
                self._cleanup(exam)

    # ---------- data ----------

    def _setup(self, n_students, n_questions):
        self._cleanup_existing()
        owner = User.objects.create_user(email=f"{PREFIX}faculty@forge.local", role="faculty")
        owner.set_unusable_password()
        owner.save()
        bank = QuestionBank.objects.create(title=f"{PREFIX}bank", owner=owner)
        exam = Exam.objects.create(
            title=f"{PREFIX}exam",
            created_by=owner,
            starts_at=timezone.now() - timedelta(minutes=1),
            ends_at=timezone.now() + timedelta(hours=1),
            duration_minutes=30,
            status=Exam.Status.SCHEDULED,
            max_attempts=1,
        )
        for i in range(n_questions):
            q = Question.objects.create(
                bank=bank, type=Question.Type.MCQ_SINGLE, text=f"Q{i}", marks=1
            )
            Option.objects.bulk_create(
                [
                    Option(question=q, text=t, is_correct=(t == "A"), order=j)
                    for j, t in enumerate("ABCD")
                ]
            )
            ExamQuestion.objects.create(exam=exam, question=q, order=i)

        users = User.objects.bulk_create(
            [
                User(email=f"{PREFIX}s{i}@forge.local", role="student", password="!")
                for i in range(n_students)
            ]
        )
        students = [
            (u, str(RefreshToken.for_user(u).access_token))
            for u in User.objects.filter(email__startswith=f"{PREFIX}s")
        ]
        self.stdout.write(f"created exam {exam.pk}, {len(users)} students, {n_questions} questions")
        return exam, students

    def _cleanup_existing(self):
        for exam in Exam.objects.filter(title__startswith=PREFIX):
            self._cleanup(exam)
        User.objects.filter(email__startswith=PREFIX).delete()

    def _cleanup(self, exam):
        attempt_ids = [
            str(pk) for pk in Attempt.objects.filter(exam=exam).values_list("pk", flat=True)
        ]
        AuditLog.objects.filter(target_type="exams.attempt", target_id__in=attempt_ids).delete()
        banks = QuestionBank.objects.filter(title__startswith=PREFIX)
        exam.delete()
        Question.objects.filter(bank__in=banks).delete()
        banks.delete()
        User.objects.filter(email__startswith=PREFIX).delete()
        self.stdout.write("cleaned up load test data")

    # ---------- traffic ----------

    def _call(self, method, path, token, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.api + path, data=data, method=method)
        req.add_header("Authorization", f"Bearer {token}")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = json.loads(resp.read() or b"null")
                return resp.status, payload, time.perf_counter() - started
        except urllib.error.HTTPError as exc:
            return (
                exc.code,
                exc.read().decode(errors="replace")[:200],
                time.perf_counter() - started,
            )
        except Exception as exc:  # connection errors count as failures
            return 0, str(exc), time.perf_counter() - started

    def _student(self, exam_id, token):
        timings, errors = {"start": [], "answer": [], "submit": []}, []
        status, data, took = self._call("POST", f"/exams/{exam_id}/start/", token)
        timings["start"].append(took)
        if status not in (200, 201):
            return timings, [f"start {status} {data}"]
        attempt_id = data["id"]
        for _round in range(2):
            for q in data["questions"]:
                choice = q["options"][_round % len(q["options"])]["id"]
                status, body, took = self._call(
                    "PUT",
                    f"/attempts/{attempt_id}/answers/{q['exam_question_id']}/",
                    token,
                    {"selected_option_ids": [choice]},
                )
                timings["answer"].append(took)
                if status != 200:
                    errors.append(f"answer {status} {body}")
        status, body, took = self._call("POST", f"/attempts/{attempt_id}/submit/", token)
        timings["submit"].append(took)
        if status != 200:
            errors.append(f"submit {status} {body}")
        return timings, errors

    def _run(self, exam, students, workers):
        all_timings = {"start": [], "answer": [], "submit": []}
        all_errors = []
        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for timings, errors in pool.map(lambda s: self._student(exam.pk, s[1]), students):
                for key, values in timings.items():
                    all_timings[key].extend(values)
                all_errors.extend(errors)
        elapsed = time.perf_counter() - started

        attempts = Attempt.objects.filter(exam=exam)
        graded = attempts.filter(status=Attempt.Status.GRADED).count()
        self.stdout.write(f"elapsed {elapsed:.1f}s, workers {workers}")
        for key, values in all_timings.items():
            if values:
                q = statistics.quantiles(values, n=100) if len(values) >= 2 else values * 99
                self.stdout.write(
                    f"{key:>7}: n={len(values)} p50={q[49] * 1000:.0f}ms p95={q[94] * 1000:.0f}ms "
                    f"max={max(values) * 1000:.0f}ms"
                )
        self.stdout.write(f"attempts {attempts.count()}, graded {graded}, errors {len(all_errors)}")
        for line in all_errors[:10]:
            self.stdout.write(f"  {line}")
        duplicates = (
            attempts.values("student").order_by().annotate(n=Count("id")).filter(n__gt=1).count()
        )
        self.stdout.write(f"students with more than one attempt: {duplicates}")
