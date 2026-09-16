import pytest
from rest_framework.throttling import ScopedRateThrottle

from apps.accounts.tests.factories import UserFactory
from apps.audit.models import AuditLog
from apps.coding import judge0
from apps.coding.models import CodeSubmission, Language, TestCase
from apps.coding.tests.factories import LanguageFactory, ProblemFactory, add_cases
from apps.coding.tests.fake_judge0 import FakeJudge0
from apps.courses.tests.factories import CourseFactory

API = "/api/v1"

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def fake_judge(monkeypatch):
    fake = FakeJudge0(token="")
    monkeypatch.setattr(
        judge0,
        "get_client",
        lambda: judge0.Judge0Client(
            base_url="http://judge0.test", token="", transport=fake.transport(), poll_interval=0
        ),
    )
    return fake


@pytest.fixture
def python():
    return LanguageFactory(slug="python", judge0_id=71)


@pytest.fixture
def problem(faculty_user):
    # sample: "1 2" -> 3 ; hidden: "10 20" -> 30, "-1 1" -> 0
    return add_cases(ProblemFactory(created_by=faculty_user, max_score=100))


def submit(client, problem, language, source):
    return client.post(
        f"{API}/problems/{problem.pk}/submit/",
        {"language": language.pk, "source_code": source},
        format="json",
    )


def run(client, problem, language, source, stdin=None):
    body = {"language": language.pk, "source_code": source}
    if stdin is not None:
        body["stdin"] = stdin
    return client.post(f"{API}/problems/{problem.pk}/run/", body, format="json")


# ---------- submit & verdicts ----------


def test_accepted_submission(auth_client, student_user, problem, python):
    res = submit(auth_client(student_user), problem, python, "SUM")
    assert res.status_code == 201, res.data
    assert (
        res.data["verdict"],
        res.data["score"],
        res.data["passed_count"],
        res.data["total_count"],
    ) == (
        "accepted",
        100,
        3,
        3,
    )
    assert res.data["status"] == "done"
    assert AuditLog.objects.filter(action="code.submit").exists()


def test_partial_and_wrong_answer(auth_client, student_user, problem, python):
    client = auth_client(student_user)
    res = submit(client, problem, python, "WRONG")  # prints 0: only "-1 1" passes
    assert (res.data["verdict"], res.data["score"], res.data["passed_count"]) == ("partial", 33, 1)
    problem.allow_partial = False
    problem.save()
    res = submit(client, problem, python, "WRONG")
    assert (res.data["verdict"], res.data["score"]) == ("wrong_answer", 0)


def test_weights_affect_partial_score(auth_client, student_user, problem, python):
    TestCase.objects.filter(problem=problem, input="-1 1").update(weight=3)
    res = submit(auth_client(student_user), problem, python, "WRONG")
    assert res.data["score"] == 60  # 3 of 5 weight


@pytest.mark.parametrize(
    ("source", "verdict"),
    [("COMPILE_ERROR", "compile_error"), ("TLE", "time_limit"), ("CRASH", "runtime_error")],
)
def test_failure_verdicts(auth_client, student_user, problem, python, source, verdict):
    res = submit(auth_client(student_user), problem, python, source)
    assert res.data["verdict"] == verdict and res.data["score"] == 0
    if verdict == "compile_error":
        assert "error" in res.data["compile_output"]


def test_output_comparison_ignores_trailing_whitespace(
    auth_client, student_user, faculty_user, python
):
    p = ProblemFactory(created_by=faculty_user)
    TestCase.objects.create(problem=p, input="1 2", expected_output="3  \r\n\r\n", is_hidden=True)
    assert submit(auth_client(student_user), p, python, "SUM").data["verdict"] == "accepted"


def test_student_view_redacts_hidden_cases(auth_client, student_user, faculty_user, python):
    p = add_cases(
        ProblemFactory(created_by=faculty_user), samples=[("1 2", "3")], hidden=[("777 1", "778")]
    )
    res = submit(auth_client(student_user), p, python, "WRONG")
    content = res.content.decode()
    assert "777 1" not in content and "778" not in content
    sample, hidden = res.data["results"]
    assert sample["input"] == "1 2" and sample["stdout"] == "0\n"
    assert hidden["hidden"] is True and "input" not in hidden and "stdout" not in hidden

    manager_view = auth_client(faculty_user).get(f"{API}/code-submissions/{res.data['id']}/")
    assert manager_view.data["results"][1]["input"] == "777 1"


def test_language_and_size_rules(auth_client, student_user, problem, python, settings):
    cpp = LanguageFactory(slug="cpp", name="C++", judge0_id=54)
    problem.allowed_languages.set([python])
    client = auth_client(student_user)
    assert submit(client, problem, cpp, "SUM").status_code == 400
    settings.CODE_SOURCE_MAX_BYTES = 10
    assert submit(client, problem, python, "SUM" * 10).status_code == 400
    assert CodeSubmission.objects.count() == 0


def test_only_students_submit_to_open_problems(auth_client, student_user, faculty_user, python):
    draft = add_cases(ProblemFactory(created_by=faculty_user, status="draft"))
    assert submit(auth_client(student_user), draft, python, "SUM").status_code == 404
    live = add_cases(ProblemFactory(created_by=faculty_user))
    assert submit(auth_client(faculty_user), live, python, "SUM").status_code == 403
    course_only = add_cases(ProblemFactory(created_by=faculty_user, course=CourseFactory()))
    assert submit(auth_client(student_user), course_only, python, "SUM").status_code == 404


def test_judge_unavailable_records_error(auth_client, student_user, problem, python, monkeypatch):
    def broken():
        raise judge0.Judge0Unavailable("down")

    class Down:
        def execute(self, requests):
            broken()

    monkeypatch.setattr(judge0, "get_client", lambda: Down())
    res = submit(auth_client(student_user), problem, python, "SUM")
    assert res.status_code == 503
    sub = CodeSubmission.objects.get()
    assert (sub.status, sub.verdict) == ("error", "internal_error")


def test_submit_is_throttled(auth_client, student_user, problem, python, monkeypatch):
    monkeypatch.setitem(ScopedRateThrottle.THROTTLE_RATES, "code_submit", "2/min")
    client = auth_client(student_user)
    codes = [submit(client, problem, python, "SUM").status_code for _ in range(3)]
    assert codes == [201, 201, 429]


# ---------- run ----------


def test_run_against_samples_is_not_stored(auth_client, student_user, problem, python):
    res = run(auth_client(student_user), problem, python, "SUM")
    assert res.status_code == 200, res.data
    assert res.data["mode"] == "samples"
    assert [(r["input"], r["passed"]) for r in res.data["results"]] == [("1 2", True)]
    assert CodeSubmission.objects.count() == 0
    assert "10 20" not in res.content.decode()


def test_run_with_custom_input(auth_client, student_user, problem, python):
    res = run(auth_client(student_user), problem, python, "SUM", stdin="40 2")
    assert res.data["mode"] == "custom"
    result = res.data["results"][0]
    assert result["stdout"] == "42\n" and result["passed"] is None


def test_manager_can_run_draft(auth_client, faculty_user, student_user, python):
    draft = add_cases(ProblemFactory(created_by=faculty_user, status="draft"))
    assert run(auth_client(faculty_user), draft, python, "SUM").status_code == 200
    assert run(auth_client(student_user), draft, python, "SUM").status_code == 404


def test_run_is_throttled(auth_client, student_user, problem, python, monkeypatch):
    monkeypatch.setitem(ScopedRateThrottle.THROTTLE_RATES, "code_run", "1/min")
    client = auth_client(student_user)
    assert run(client, problem, python, "SUM").status_code == 200
    assert run(client, problem, python, "SUM").status_code == 429


# ---------- history ----------


def test_submission_history_visibility(auth_client, student_user, faculty_user, problem, python):
    other = UserFactory(role="student")
    mine = submit(auth_client(student_user), problem, python, "SUM").data["id"]
    theirs = submit(auth_client(other), problem, python, "WRONG").data["id"]

    own_list = (
        auth_client(student_user).get(f"{API}/problems/{problem.pk}/submissions/").data["results"]
    )
    assert [s["id"] for s in own_list] == [mine]
    assert "source_code" not in own_list[0]

    staff_list = (
        auth_client(faculty_user)
        .get(f"{API}/problems/{problem.pk}/submissions/", {"student": other.pk})
        .data["results"]
    )
    assert [s["id"] for s in staff_list] == [theirs]

    assert auth_client(student_user).get(f"{API}/code-submissions/{theirs}/").status_code == 404
    detail = auth_client(student_user).get(f"{API}/code-submissions/{mine}/")
    assert detail.status_code == 200 and detail.data["source_code"] == "SUM"


def test_rejudge_after_fixing_test_case(auth_client, student_user, faculty_user, problem, python):
    sub_id = submit(auth_client(student_user), problem, python, "SUM").data["id"]
    TestCase.objects.filter(problem=problem, input="-1 1").update(expected_output="5")
    res = auth_client(faculty_user).post(f"{API}/problems/{problem.pk}/rejudge/")
    assert res.status_code == 200 and res.data == {"rejudged": 1, "failed": 0}
    assert CodeSubmission.objects.get(pk=sub_id).verdict == "partial"
    assert AuditLog.objects.filter(action="problem.rejudge").exists()
    assert (
        auth_client(student_user).post(f"{API}/problems/{problem.pk}/rejudge/").status_code == 403
    )


# ---------- leaderboard & summary ----------


def test_leaderboard_best_score_per_student(auth_client, student_user, problem, python):
    a = UserFactory(role="student", first_name="Ada", last_name="L")
    b = UserFactory(role="student", first_name="Bob", last_name="K")
    submit(auth_client(a), problem, python, "WRONG")
    submit(auth_client(b), problem, python, "SUM")
    submit(auth_client(a), problem, python, "SUM")
    submit(auth_client(a), problem, python, "WRONG")
    rows = auth_client(student_user).get(f"{API}/problems/{problem.pk}/leaderboard/").data
    assert [(r["name"], r["best_score"], r["attempts"]) for r in rows] == [
        ("Bob K", 100, 1),
        ("Ada L", 100, 3),
    ]


def test_my_summary_and_problem_status(auth_client, student_user, faculty_user, python):
    solved = add_cases(ProblemFactory(created_by=faculty_user, title="solved"))
    tried = add_cases(ProblemFactory(created_by=faculty_user, title="tried"))
    client = auth_client(student_user)
    submit(client, solved, python, "SUM")
    submit(client, tried, python, "WRONG")
    summary = client.get(f"{API}/me/coding/summary/").data
    assert (summary["solved"], summary["attempted"], summary["submissions"]) == (1, 2, 2)
    assert len(summary["recent"]) == 2
    rows = {p["title"]: p["my_status"] for p in client.get(f"{API}/problems/").data["results"]}
    assert rows["solved"]["solved"] is True and rows["tried"]["best_score"] == 33
    assert Language.objects.count() >= 1
