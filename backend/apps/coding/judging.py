"""Run and submit code. Filled in by the judging step."""

from django.db.models import Max

from .models import CodeSubmission


def student_problem_stats(user):
    stats = {}
    rows = (
        CodeSubmission.objects.filter(student=user, status=CodeSubmission.Status.DONE)
        .values("problem_id")
        .annotate(best=Max("score"))
    )
    counts = {}
    for sub in CodeSubmission.objects.filter(student=user).values_list("problem_id", "verdict"):
        counts.setdefault(sub[0], []).append(sub[1])
    for row in rows:
        verdicts = counts.get(row["problem_id"], [])
        stats[row["problem_id"]] = {
            "attempts": len(verdicts),
            "best_score": row["best"] or 0,
            "solved": CodeSubmission.Verdict.ACCEPTED in verdicts,
        }
    return stats
