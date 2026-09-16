import httpx
import pytest

from apps.coding.judge0 import ExecRequest, Judge0Client, Judge0Error, Judge0Unavailable
from apps.coding.tests.fake_judge0 import FakeJudge0


def client_for(fake, **kwargs):
    kwargs.setdefault("poll_interval", 0)
    return Judge0Client(
        base_url="http://judge0.test", token="test-token", transport=fake.transport(), **kwargs
    )


def req(source="SUM", stdin="1 2"):
    return ExecRequest(
        source_code=source, language_id=71, stdin=stdin, cpu_time_limit=2, memory_limit=128000
    )


def test_execute_polls_until_finished_and_decodes_output():
    fake = FakeJudge0()
    results = client_for(fake).execute([req("SUM", "2 3"), req("WRONG", "2 3")])
    assert [r.status_id for r in results] == [3, 3]
    assert [r.stdout for r in results] == ["5\n", "0\n"]
    assert results[0].time == pytest.approx(0.01) and results[0].memory == 3200
    assert all(count == 2 for count in fake.polls.values())


def test_sends_base64_and_limits():
    fake = FakeJudge0()
    client_for(fake).execute([req("SUM", "7 8")])
    sent = fake.last_request_bodies[0]["submissions"][0]
    assert (
        sent["language_id"] == 71 and sent["cpu_time_limit"] == 2 and sent["memory_limit"] == 128000
    )
    assert sent["source_code"] == "U1VN"  # base64("SUM")


def test_statuses_for_compile_error_tle_and_crash():
    fake = FakeJudge0()
    results = client_for(fake).execute([req("COMPILE_ERROR"), req("TLE"), req("CRASH")])
    assert [r.status_id for r in results] == [6, 5, 11]
    assert results[0].compile_output == "main.c:1: error"
    assert results[2].stderr == "Traceback"


def test_large_runs_are_split_into_batches():
    fake = FakeJudge0(batch_limit=20)
    results = client_for(fake).execute([req("SUM", f"{i} 1") for i in range(45)])
    assert fake.batch_posts == 3
    assert [r.stdout for r in results][:3] == ["1\n", "2\n", "3\n"]


def test_wrong_token_raises_judge0_error():
    fake = FakeJudge0(token="expected")
    with pytest.raises(Judge0Error, match="authentication"):
        client_for(fake).execute([req()])


def test_connection_failure_raises_unavailable():
    def refuse(request):
        raise httpx.ConnectError("refused", request=request)

    client = Judge0Client(
        base_url="http://judge0.test", transport=httpx.MockTransport(refuse), poll_interval=0
    )
    with pytest.raises(Judge0Unavailable):
        client.execute([req()])


def test_gives_up_when_results_never_finish():
    def stuck(request):
        if request.method == "POST":
            return httpx.Response(201, json=[{"token": "t1"}])
        return httpx.Response(200, json={"submissions": [{"token": "t1", "status": {"id": 1}}]})

    client = Judge0Client(
        base_url="http://judge0.test",
        transport=httpx.MockTransport(stuck),
        poll_interval=0,
        timeout_seconds=0.05,
    )
    with pytest.raises(Judge0Error, match="did not finish"):
        client.execute([req()])


def test_languages():
    fake = FakeJudge0()
    assert client_for(fake).languages()[0]["id"] == 71


@pytest.mark.judge0
def test_live_judge0_runs_python():
    """Runs only when a real Judge0 is reachable (see infra/judge0/README.md)."""
    from django.conf import settings

    client = Judge0Client()
    try:
        client.languages()
    except Judge0Unavailable:
        pytest.skip(f"Judge0 not reachable at {settings.JUDGE0_URL}")
    result = client.execute(
        [
            ExecRequest(
                source_code="print(sum(map(int, input().split())))", language_id=71, stdin="4 5"
            )
        ]
    )[0]
    assert result.status_id == 3 and result.stdout.strip() == "9"
