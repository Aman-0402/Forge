"""Run and judge code against a problem's test cases."""

from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Max, Min
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.audit.services import log_action

from . import judge0
from .models import CodeSubmission, TestCaseResult

Verdict = CodeSubmission.Verdict


# ---------- helpers ----------


def normalise(text):
    lines = (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    lines = [line.rstrip() for line in lines]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def clip(text):
    limit = settings.CODE_OUTPUT_MAX_CHARS
    text = text or ""
    return text if len(text) <= limit else text[:limit] + "\n…[truncated]"


def check_source(problem, language, source_code):
    if not problem.languages().filter(pk=language.pk).exists():
        raise ValidationError({"language": ["This language is not allowed for this problem."]})
    if not source_code.strip():
        raise ValidationError({"source_code": ["Write some code first."]})
    if len(source_code.encode("utf-8")) > settings.CODE_SOURCE_MAX_BYTES:
        raise ValidationError(
            {"source_code": [f"Source is larger than {settings.CODE_SOURCE_MAX_BYTES} bytes."]}
        )


def exec_request(problem, language, source_code, stdin):
    return judge0.ExecRequest(
        source_code=source_code,
        language_id=language.judge0_id,
        stdin=stdin,
        cpu_time_limit=float(problem.time_limit_seconds),
        memory_limit=problem.memory_limit_kb,
    )


def case_verdict(execution, expected, memory_limit_kb):
    """Return (verdict, passed) for one test-case execution."""
    status = execution.status_id
    if status == judge0.STATUS_COMPILE_ERROR:
        return Verdict.COMPILE_ERROR, False
    if status == judge0.STATUS_TIME_LIMIT:
        return Verdict.TIME_LIMIT, False
    if status in judge0.RUNTIME_ERROR_IDS:
        if execution.memory and execution.memory >= memory_limit_kb:
            return Verdict.MEMORY_LIMIT, False
        return Verdict.RUNTIME_ERROR, False
    if status in (judge0.STATUS_ACCEPTED, judge0.STATUS_WRONG_ANSWER):
        if normalise(execution.stdout) == normalise(expected):
            return Verdict.ACCEPTED, True
        return Verdict.WRONG_ANSWER, False
    return Verdict.INTERNAL_ERROR, False


def aggregate(problem, cases, verdicts):
    """Overall (verdict, score, passed_count) from per-case verdicts."""
    passed = [c for c, (_, ok) in zip(cases, verdicts, strict=True) if ok]
    total_weight = sum(c.weight for c in cases) or 1
    passed_weight = sum(c.weight for c in passed)
    kinds = [v for v, _ in verdicts]

    if Verdict.COMPILE_ERROR in kinds:
        return Verdict.COMPILE_ERROR, 0, 0
    if Verdict.INTERNAL_ERROR in kinds:
        return Verdict.INTERNAL_ERROR, 0, len(passed)
    if len(passed) == len(cases):
        return Verdict.ACCEPTED, problem.max_score, len(passed)
    if passed and problem.allow_partial:
        return Verdict.PARTIAL, problem.max_score * passed_weight // total_weight, len(passed)
    first_failure = next(v for v, ok in verdicts if not ok)
    return first_failure, 0, len(passed)


# ---------- run (not stored) ----------


def run_code(*, problem, language, source_code, stdin=None):
    check_source(problem, language, source_code)
    client = judge0.get_client()
    if stdin is not None:
        execution = client.execute([exec_request(problem, language, source_code, stdin)])[0]
        return {
            "mode": "custom",
            "compile_output": clip(execution.compile_output),
            "results": [
                {
                    "index": 1,
                    "input": stdin,
                    "expected_output": None,
                    "stdout": clip(execution.stdout),
                    "stderr": clip(execution.stderr),
                    "status": execution.status,
                    "verdict": None,
                    "passed": None,
                    "time_seconds": execution.time,
                    "memory_kb": execution.memory,
                }
            ],
        }

    samples = [c for c in problem.test_cases.all() if c.is_sample and not c.is_hidden]
    if not samples:
        raise ValidationError(
            {"detail": ["This problem has no sample cases. Provide custom input."]}
        )
    executions = client.execute(
        [exec_request(problem, language, source_code, c.input) for c in samples]
    )
    results = []
    compile_output = ""
    for index, (case, execution) in enumerate(zip(samples, executions, strict=True), start=1):
        verdict, passed = case_verdict(execution, case.expected_output, problem.memory_limit_kb)
        compile_output = compile_output or execution.compile_output
        results.append(
            {
                "index": index,
                "input": case.input,
                "expected_output": case.expected_output,
                "stdout": clip(execution.stdout),
                "stderr": clip(execution.stderr),
                "status": execution.status,
                "verdict": verdict,
                "passed": passed,
                "time_seconds": execution.time,
                "memory_kb": execution.memory,
            }
        )
    return {"mode": "samples", "compile_output": clip(compile_output), "results": results}


# ---------- submit (stored) ----------


def judge_submission(submission):
    """Run a stored submission against all test cases and save the outcome.

    Raises ``judge0.Judge0Error`` after marking the submission as errored.
    """
    problem = submission.problem
    cases = list(problem.test_cases.all())
    submission.status = CodeSubmission.Status.RUNNING
    submission.save(update_fields=["status"])

    try:
        executions = judge0.get_client().execute(
            [
                exec_request(problem, submission.language, submission.source_code, c.input)
                for c in cases
            ]
        )
    except judge0.Judge0Error:
        submission.status = CodeSubmission.Status.ERROR
        submission.verdict = Verdict.INTERNAL_ERROR
        submission.score = 0
        submission.judged_at = timezone.now()
        submission.save(update_fields=["status", "verdict", "score", "judged_at"])
        raise

    verdicts = [
        case_verdict(e, c.expected_output, problem.memory_limit_kb)
        for c, e in zip(cases, executions, strict=True)
    ]
    verdict, score, passed_count = aggregate(problem, cases, verdicts)

    with transaction.atomic():
        submission.results.all().delete()
        TestCaseResult.objects.bulk_create(
            [
                TestCaseResult(
                    submission=submission,
                    test_case=case,
                    judge0_token=execution.token,
                    verdict=case_v,
                    passed=ok,
                    stdout=clip(execution.stdout),
                    stderr=clip(execution.stderr),
                    time_seconds=Decimal(str(execution.time))
                    if execution.time is not None
                    else None,
                    memory_kb=execution.memory,
                    order=index,
                )
                for index, (case, execution, (case_v, ok)) in enumerate(
                    zip(cases, executions, verdicts, strict=True)
                )
            ]
        )
        times = [e.time for e in executions if e.time is not None]
        memories = [e.memory for e in executions if e.memory is not None]
        submission.status = CodeSubmission.Status.DONE
        submission.verdict = verdict
        submission.score = score
        submission.passed_count = passed_count
        submission.total_count = len(cases)
        submission.max_time_seconds = Decimal(str(max(times))) if times else None
        submission.max_memory_kb = max(memories) if memories else None
        submission.compile_output = clip(
            next((e.compile_output for e in executions if e.compile_output), "")
        )
        submission.judged_at = timezone.now()
        submission.save()
    return submission


def submit_code(*, student, problem, language, source_code, request=None):
    check_source(problem, language, source_code)
    submission = CodeSubmission.objects.create(
        problem=problem,
        student=student,
        language=language,
        source_code=source_code,
        total_count=problem.test_cases.count(),
    )
    log_action(
        student,
        "code.submit",
        target=submission,
        metadata={"problem": problem.pk, "language": language.slug},
        request=request,
    )
    return judge_submission(submission)


def rejudge_problem(*, actor, problem, request=None):
    rejudged = failed = 0
    for submission in problem.submissions.select_related("language", "problem").order_by("id"):
        try:
            judge_submission(submission)
            rejudged += 1
        except judge0.Judge0Error:
            failed += 1
    log_action(
        actor,
        "problem.rejudge",
        target=problem,
        metadata={"rejudged": rejudged, "failed": failed},
        request=request,
    )
    return {"rejudged": rejudged, "failed": failed}


# ---------- stats ----------


def student_problem_stats(user):
    rows = (
        CodeSubmission.objects.filter(student=user)
        .values("problem_id")
        .annotate(attempts=Count("id"), best=Max("score"))
    )
    solved = set(
        CodeSubmission.objects.filter(student=user, verdict=Verdict.ACCEPTED).values_list(
            "problem_id", flat=True
        )
    )
    return {
        row["problem_id"]: {
            "attempts": row["attempts"],
            "best_score": row["best"] or 0,
            "solved": row["problem_id"] in solved,
        }
        for row in rows
    }


def leaderboard(problem, limit=50):
    rows = list(
        problem.submissions.filter(status=CodeSubmission.Status.DONE)
        .values("student_id", "student__first_name", "student__last_name", "student__email")
        .annotate(best_score=Max("score"), attempts=Count("id"))
        .filter(best_score__gt=0)
    )
    # When did each student first reach their best score? Earlier ranks higher on ties.
    for row in rows:
        row["reached_at"] = problem.submissions.filter(
            student_id=row["student_id"], score=row["best_score"]
        ).aggregate(first=Min("submitted_at"))["first"]
    rows.sort(key=lambda r: (-r["best_score"], r["reached_at"]))
    return [
        {
            "rank": rank,
            "student_id": r["student_id"],
            "name": f"{r['student__first_name']} {r['student__last_name']}".strip()
            or r["student__email"].split("@")[0],
            "best_score": r["best_score"],
            "attempts": r["attempts"],
            "reached_at": r["reached_at"],
        }
        for rank, r in enumerate(rows[:limit], start=1)
    ]
