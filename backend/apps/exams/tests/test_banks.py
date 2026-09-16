import pytest

from apps.accounts.tests.factories import UserFactory
from apps.audit.models import AuditLog
from apps.exams.models import Question
from apps.exams.tests.factories import (
    ExamFactory,
    QuestionBankFactory,
    add_questions,
    mcq,
    subjective,
)

API = "/api/v1"

pytestmark = pytest.mark.django_db


def mcq_body(**overrides):
    body = {
        "type": "mcq_single",
        "text": "2 + 2 = ?",
        "marks": "2",
        "negative_marks": "0.5",
        "difficulty": "easy",
        "tags": ["arithmetic"],
        "options": [
            {"text": "3", "is_correct": False},
            {"text": "4", "is_correct": True},
            {"text": "5", "is_correct": False},
        ],
    }
    body.update(overrides)
    return body


# ---------- banks ----------


def test_faculty_creates_bank_and_students_are_blocked(auth_client, faculty_user, student_user):
    res = auth_client(faculty_user).post(
        f"{API}/question-banks/", {"title": "Algebra"}, format="json"
    )
    assert res.status_code == 201, res.data
    assert res.data["owner"] == faculty_user.pk
    assert auth_client(student_user).get(f"{API}/question-banks/").status_code == 403
    assert AuditLog.objects.filter(action="question_bank.create").exists()


def test_bank_visibility(auth_client, admin_user, faculty_user):
    QuestionBankFactory(owner=faculty_user, title="mine")
    QuestionBankFactory(title="shared", is_shared=True)
    QuestionBankFactory(title="private")

    def titles(user):
        return {b["title"] for b in auth_client(user).get(f"{API}/question-banks/").data["results"]}

    assert titles(faculty_user) == {"mine", "shared"}
    assert titles(admin_user) == {"mine", "shared", "private"}


def test_only_owner_or_admin_edits_bank(auth_client, admin_user, faculty_user):
    shared = QuestionBankFactory(is_shared=True)
    url = f"{API}/question-banks/{shared.pk}/"
    assert auth_client(faculty_user).get(url).status_code == 200
    assert auth_client(faculty_user).patch(url, {"title": "x"}, format="json").status_code == 403
    assert auth_client(admin_user).patch(url, {"title": "x"}, format="json").status_code == 200
    private = QuestionBankFactory()
    assert auth_client(faculty_user).get(f"{API}/question-banks/{private.pk}/").status_code == 404


# ---------- questions ----------


def test_create_mcq_with_options(auth_client, faculty_user):
    bank = QuestionBankFactory(owner=faculty_user)
    res = auth_client(faculty_user).post(
        f"{API}/question-banks/{bank.pk}/questions/", mcq_body(), format="json"
    )
    assert res.status_code == 201, res.data
    assert [o["is_correct"] for o in res.data["options"]] == [False, True, False]
    assert res.data["tags"] == ["arithmetic"]


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"options": [{"text": "only", "is_correct": True}]}, "options"),
        (
            {"options": [{"text": "a", "is_correct": False}, {"text": "b", "is_correct": False}]},
            "options",
        ),
        (
            {"options": [{"text": "a", "is_correct": True}, {"text": "b", "is_correct": True}]},
            "options",
        ),
        ({"negative_marks": "3"}, "negative_marks"),
        ({"type": "true_false"}, "options"),
    ],
)
def test_objective_option_rules(auth_client, faculty_user, overrides, field):
    bank = QuestionBankFactory(owner=faculty_user)
    res = auth_client(faculty_user).post(
        f"{API}/question-banks/{bank.pk}/questions/", mcq_body(**overrides), format="json"
    )
    assert res.status_code == 400
    assert field in res.data["errors"]


def test_multi_answer_and_true_false_and_subjective(auth_client, faculty_user):
    bank = QuestionBankFactory(owner=faculty_user)
    url = f"{API}/question-banks/{bank.pk}/questions/"
    client = auth_client(faculty_user)
    multi = mcq_body(
        type="mcq_multi",
        options=[
            {"text": "a", "is_correct": True},
            {"text": "b", "is_correct": True},
            {"text": "c", "is_correct": False},
        ],
    )
    assert client.post(url, multi, format="json").status_code == 201
    tf = mcq_body(
        type="true_false",
        options=[{"text": "True", "is_correct": True}, {"text": "False", "is_correct": False}],
    )
    assert client.post(url, tf, format="json").status_code == 201
    essay = {"type": "subjective", "text": "Explain recursion.", "marks": "10"}
    res = client.post(url, essay, format="json")
    assert res.status_code == 201 and res.data["options"] == []
    with_options = dict(essay, options=[{"text": "x", "is_correct": True}])
    assert client.post(url, with_options, format="json").status_code == 400


def test_non_owner_cannot_add_questions(auth_client):
    bank = QuestionBankFactory(is_shared=True)
    other = UserFactory(role="faculty")
    res = auth_client(other).post(
        f"{API}/question-banks/{bank.pk}/questions/", mcq_body(), format="json"
    )
    assert res.status_code == 403


def test_list_questions_filters(auth_client, faculty_user):
    bank = QuestionBankFactory(owner=faculty_user)
    mcq(bank=bank, difficulty="hard", text="Hard one")
    subjective(bank=bank, text="Essay one")
    client = auth_client(faculty_user)
    url = f"{API}/question-banks/{bank.pk}/questions/"
    assert [q["text"] for q in client.get(url, {"type": "subjective"}).data["results"]] == [
        "Essay one"
    ]
    assert [q["text"] for q in client.get(url, {"difficulty": "hard"}).data["results"]] == [
        "Hard one"
    ]
    assert [q["text"] for q in client.get(url, {"search": "essay"}).data["results"]] == [
        "Essay one"
    ]


def test_update_replaces_options(auth_client, faculty_user):
    bank = QuestionBankFactory(owner=faculty_user)
    q = mcq(bank=bank)
    res = auth_client(faculty_user).patch(
        f"{API}/questions/{q.pk}/",
        {
            "text": "New text",
            "options": [{"text": "yes", "is_correct": True}, {"text": "no", "is_correct": False}],
        },
        format="json",
    )
    assert res.status_code == 200, res.data
    q.refresh_from_db()
    assert q.text == "New text" and q.options.count() == 2


def test_question_used_by_attempted_exam_is_locked(auth_client, faculty_user, student_user):
    from apps.exams.models import Attempt

    bank = QuestionBankFactory(owner=faculty_user)
    q = mcq(bank=bank)
    exam = add_questions(ExamFactory(created_by=faculty_user), q)
    Attempt.objects.create(exam=exam, student=student_user, deadline_at=exam.ends_at)
    client = auth_client(faculty_user)
    assert (
        client.patch(f"{API}/questions/{q.pk}/", {"text": "changed"}, format="json").status_code
        == 400
    )
    assert (
        client.patch(f"{API}/questions/{q.pk}/", {"is_active": False}, format="json").status_code
        == 200
    )


def test_delete_question_in_exam_is_blocked(auth_client, faculty_user):
    bank = QuestionBankFactory(owner=faculty_user)
    used = mcq(bank=bank)
    free = mcq(bank=bank)
    add_questions(ExamFactory(created_by=faculty_user, status="draft"), used)
    client = auth_client(faculty_user)
    assert client.delete(f"{API}/questions/{used.pk}/").status_code == 400
    assert client.delete(f"{API}/questions/{free.pk}/").status_code == 204


# ---------- import ----------


def test_import_all_or_nothing(auth_client, faculty_user):
    bank = QuestionBankFactory(owner=faculty_user)
    url = f"{API}/question-banks/{bank.pk}/import/"
    client = auth_client(faculty_user)
    bad = {"questions": [mcq_body(), mcq_body(options=[{"text": "x", "is_correct": True}])]}
    res = client.post(url, bad, format="json")
    assert res.status_code == 400
    assert "1" in res.data["errors"]["questions"]
    assert Question.objects.count() == 0

    good = {"questions": [mcq_body(), {"type": "subjective", "text": "Why?", "marks": "5"}]}
    res = client.post(url, good, format="json")
    assert res.status_code == 201, res.data
    assert res.data == {"created": 2}
    assert bank.questions.count() == 2


def test_filter_questions_by_tag(auth_client, faculty_user):
    bank = QuestionBankFactory(owner=faculty_user)
    mcq(bank=bank, text="Tagged", tags=["loops", "basics"])
    mcq(bank=bank, text="Other", tags=["graphs"])
    res = auth_client(faculty_user).get(
        f"{API}/question-banks/{bank.pk}/questions/", {"tag": "loops", "type": "mcq_single"}
    )
    assert [q["text"] for q in res.data["results"]] == ["Tagged"]
