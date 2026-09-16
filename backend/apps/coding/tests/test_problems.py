from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.tests.factories import UserFactory
from apps.audit.models import AuditLog
from apps.coding.models import Language, Problem, TestCase
from apps.coding.tests.factories import LanguageFactory, ProblemFactory, add_cases
from apps.courses.tests.factories import CourseFactory, EnrollmentFactory

API = "/api/v1"

pytestmark = pytest.mark.django_db


def body(**overrides):
    data = {
        "title": "Sum of two numbers",
        "statement": "Print a + b.",
        "input_format": "Two integers",
        "output_format": "One integer",
        "difficulty": "easy",
        "time_limit_seconds": "1",
        "memory_limit_kb": 64000,
        "tags": ["math"],
    }
    data.update(overrides)
    return data


# ---------- languages ----------


def test_seed_languages_is_idempotent_and_listed(auth_client, student_user):
    call_command("seed_languages")
    call_command("seed_languages")
    assert Language.objects.count() == 5
    rows = auth_client(student_user).get(f"{API}/languages/").data
    assert {r["slug"] for r in rows} >= {"python", "cpp", "java"}
    assert all("judge0_id" in r and "default_template" in r for r in rows)


def test_disabled_languages_hidden(auth_client, student_user):
    call_command("seed_languages")
    Language.objects.filter(slug="java").update(is_enabled=False)
    slugs = {r["slug"] for r in auth_client(student_user).get(f"{API}/languages/").data}
    assert "java" not in slugs


# ---------- problems ----------


def test_faculty_creates_draft_problem(auth_client, faculty_user):
    res = auth_client(faculty_user).post(f"{API}/problems/", body(), format="json")
    assert res.status_code == 201, res.data
    assert res.data["status"] == "draft" and res.data["slug"] == "sum-of-two-numbers"
    assert res.data["created_by"] == faculty_user.pk
    assert AuditLog.objects.filter(action="problem.create").exists()


def test_student_cannot_create(auth_client, student_user):
    assert (
        auth_client(student_user).post(f"{API}/problems/", body(), format="json").status_code == 403
    )


def test_course_problem_requires_managing_course(auth_client, faculty_user):
    client = auth_client(faculty_user)
    other = CourseFactory()
    assert client.post(f"{API}/problems/", body(course=other.pk), format="json").status_code == 400
    mine = CourseFactory(instructor=faculty_user)
    assert client.post(f"{API}/problems/", body(course=mine.pk), format="json").status_code == 201


def test_allowed_languages_must_be_enabled(auth_client, faculty_user):
    off = LanguageFactory(judge0_id=62, slug="java", name="Java", is_enabled=False)
    res = auth_client(faculty_user).post(
        f"{API}/problems/", body(allowed_languages=[off.pk]), format="json"
    )
    assert res.status_code == 400


def test_student_visibility(auth_client, student_user):
    now = timezone.now()
    ProblemFactory(title="open")
    ProblemFactory(title="draft", status="draft")
    ProblemFactory(title="future", visible_from=now + timedelta(days=1))
    ProblemFactory(title="expired", visible_until=now - timedelta(days=1))
    course = CourseFactory()
    ProblemFactory(title="course not enrolled", course=course)
    enrolled_course = CourseFactory()
    EnrollmentFactory(course=enrolled_course, student=student_user)
    ProblemFactory(title="course enrolled", course=enrolled_course)

    titles = {p["title"] for p in auth_client(student_user).get(f"{API}/problems/").data["results"]}
    assert titles == {"open", "course enrolled"}


def test_staff_visibility(auth_client, admin_user, faculty_user):
    ProblemFactory(title="published by other")
    ProblemFactory(title="draft by other", status="draft")
    ProblemFactory(title="my draft", status="draft", created_by=faculty_user)

    def titles(user):
        return {p["title"] for p in auth_client(user).get(f"{API}/problems/").data["results"]}

    assert titles(faculty_user) == {"published by other", "my draft"}
    assert len(titles(admin_user)) == 3


def test_filters(auth_client, student_user):
    ProblemFactory(title="Easy one", difficulty="easy", tags=["arrays"])
    ProblemFactory(title="Hard one", difficulty="hard", tags=["graphs"])
    client = auth_client(student_user)
    assert [
        p["title"] for p in client.get(f"{API}/problems/", {"difficulty": "hard"}).data["results"]
    ] == ["Hard one"]
    assert [
        p["title"] for p in client.get(f"{API}/problems/", {"tag": "arrays"}).data["results"]
    ] == ["Easy one"]
    assert [
        p["title"] for p in client.get(f"{API}/problems/", {"search": "hard"}).data["results"]
    ] == ["Hard one"]


def test_student_detail_shows_samples_only(auth_client, student_user):
    problem = add_cases(
        ProblemFactory(), samples=[("1 2", "3")], hidden=[("SECRET_IN", "SECRET_OUT")]
    )
    res = auth_client(student_user).get(f"{API}/problems/{problem.pk}/")
    assert res.status_code == 200
    content = res.content.decode()
    assert "SECRET_IN" not in content and "SECRET_OUT" not in content
    assert res.data["sample_cases"] == [{"input": "1 2", "expected_output": "3", "explanation": ""}]
    assert res.data["test_case_count"] == 2


def test_problem_update_is_manager_only(auth_client, faculty_user):
    problem = ProblemFactory(created_by=faculty_user)
    other = UserFactory(role="faculty")
    url = f"{API}/problems/{problem.pk}/"
    assert auth_client(other).patch(url, {"title": "x"}, format="json").status_code == 403
    assert auth_client(faculty_user).patch(url, {"title": "x"}, format="json").status_code == 200


# ---------- test cases ----------


def test_manager_manages_test_cases(auth_client, faculty_user, student_user):
    problem = ProblemFactory(created_by=faculty_user, status="draft")
    url = f"{API}/problems/{problem.pk}/testcases/"
    client = auth_client(faculty_user)
    res = client.post(
        url,
        {"input": "1 2", "expected_output": "3", "is_sample": True, "is_hidden": False},
        format="json",
    )
    assert res.status_code == 201, res.data
    res = client.post(url, {"input": "5 5", "expected_output": "10", "weight": 2}, format="json")
    assert res.status_code == 201 and res.data["is_hidden"] is True
    assert len(client.get(url).data) == 2

    case_id = res.data["id"]
    assert (
        client.patch(f"{API}/testcases/{case_id}/", {"weight": 3}, format="json").status_code == 200
    )
    assert client.delete(f"{API}/testcases/{case_id}/").status_code == 204

    assert auth_client(student_user).get(url).status_code in (403, 404)
    other = UserFactory(role="faculty")
    # Other faculty cannot see a draft at all (404); on a published problem they get 403.
    assert (
        auth_client(other)
        .post(url, {"input": "", "expected_output": ""}, format="json")
        .status_code
        == 404
    )
    problem.status = "published"
    problem.save()
    assert (
        auth_client(other)
        .post(url, {"input": "", "expected_output": ""}, format="json")
        .status_code
        == 403
    )


def test_sample_case_cannot_be_hidden(auth_client, faculty_user):
    problem = ProblemFactory(created_by=faculty_user)
    res = auth_client(faculty_user).post(
        f"{API}/problems/{problem.pk}/testcases/",
        {"input": "1", "expected_output": "1", "is_sample": True, "is_hidden": True},
        format="json",
    )
    assert res.status_code == 400


def test_bulk_import_test_cases(auth_client, faculty_user):
    problem = ProblemFactory(created_by=faculty_user)
    res = auth_client(faculty_user).post(
        f"{API}/problems/{problem.pk}/testcases/import/",
        {
            "cases": [
                {"input": "1 1", "expected_output": "2", "is_sample": True},
                {"input": "2 2", "expected_output": "4"},
            ]
        },
        format="json",
    )
    assert res.status_code == 201, res.data
    assert res.data == {"created": 2}
    assert TestCase.objects.filter(problem=problem, is_sample=True, is_hidden=False).count() == 1


# ---------- lifecycle ----------


def test_publish_requires_test_cases(auth_client, faculty_user):
    problem = ProblemFactory(created_by=faculty_user, status="draft")
    client = auth_client(faculty_user)
    assert client.post(f"{API}/problems/{problem.pk}/publish/").status_code == 400
    add_cases(problem)
    res = client.post(f"{API}/problems/{problem.pk}/publish/")
    assert res.status_code == 200 and res.data["status"] == "published"
    assert client.post(f"{API}/problems/{problem.pk}/archive/").data["status"] == "archived"
    assert AuditLog.objects.filter(action="problem.publish").exists()
    assert Problem.objects.get(pk=problem.pk).status == "archived"
