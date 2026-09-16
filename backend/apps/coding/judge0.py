"""Minimal Judge0 CE REST client.

Only the calls Forge needs: list languages, create a batch of submissions, and poll the
batch until every item has finished. All text crosses the wire base64-encoded so any
bytes in source, stdin or output survive.
"""

import base64
import time
from dataclasses import dataclass

import httpx
from django.conf import settings

BATCH_SIZE = 20  # Judge0 CE default MAX_SUBMISSION_BATCH_SIZE
FINISHED_FROM = 3  # status ids 1 (In Queue) and 2 (Processing) are unfinished

STATUS_ACCEPTED = 3
STATUS_WRONG_ANSWER = 4
STATUS_TIME_LIMIT = 5
STATUS_COMPILE_ERROR = 6
RUNTIME_ERROR_IDS = range(7, 13)  # SIGSEGV, SIGXFSZ, SIGFPE, SIGABRT, NZEC, Other
STATUS_INTERNAL_ERROR = 13
STATUS_EXEC_FORMAT_ERROR = 14


class Judge0Error(Exception):
    """Judge0 answered, but not with something usable."""


class Judge0Unavailable(Judge0Error):
    """Judge0 could not be reached."""


@dataclass
class ExecRequest:
    source_code: str
    language_id: int
    stdin: str = ""
    cpu_time_limit: float | None = None
    memory_limit: int | None = None


@dataclass
class Execution:
    token: str
    status_id: int
    status: str = ""
    stdout: str = ""
    stderr: str = ""
    compile_output: str = ""
    message: str = ""
    time: float | None = None
    memory: int | None = None


def _encode(text):
    return base64.b64encode((text or "").encode("utf-8")).decode("ascii")


def _decode(text):
    if not text:
        return ""
    return base64.b64decode(text).decode("utf-8", errors="replace")


class Judge0Client:
    def __init__(
        self,
        base_url=None,
        token=None,
        timeout_seconds=None,
        transport=None,
        poll_interval=0.5,
        sleep=time.sleep,
    ):
        self.base_url = (base_url or settings.JUDGE0_URL).rstrip("/")
        self.token = settings.JUDGE0_AUTH_TOKEN if token is None else token
        self.timeout_seconds = timeout_seconds or settings.JUDGE0_TIMEOUT_SECONDS
        self.transport = transport
        self.poll_interval = poll_interval
        self.sleep = sleep

    # ---------- http ----------

    def _http(self):
        headers = {"X-Auth-Token": self.token} if self.token else {}
        return httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=httpx.Timeout(10.0),
            transport=self.transport,
        )

    def _request(self, http, method, path, **kwargs):
        try:
            response = http.request(method, path, **kwargs)
        except (httpx.TransportError, httpx.TimeoutException) as exc:
            raise Judge0Unavailable(f"Cannot reach Judge0 at {self.base_url}: {exc}") from exc
        if response.status_code in (401, 403):
            raise Judge0Error("Judge0 rejected the request: authentication failed.")
        if response.status_code >= 400:
            raise Judge0Error(f"Judge0 returned {response.status_code}: {response.text[:300]}")
        return response.json()

    # ---------- api ----------

    def languages(self):
        with self._http() as http:
            return self._request(http, "GET", "/languages")

    def execute(self, requests):
        """Run every request and return an ``Execution`` per request, in the same order."""
        if not requests:
            return []
        with self._http() as http:
            tokens = []
            for start in range(0, len(requests), BATCH_SIZE):
                tokens.extend(self._create(http, requests[start : start + BATCH_SIZE]))
            return self._wait(http, tokens)

    def _create(self, http, chunk):
        payload = {"submissions": [self._payload(r) for r in chunk]}
        rows = self._request(
            http, "POST", "/submissions/batch", params={"base64_encoded": "true"}, json=payload
        )
        tokens = [row.get("token") for row in rows]
        if len(tokens) != len(chunk) or not all(tokens):
            raise Judge0Error(f"Judge0 refused part of the batch: {rows}")
        return tokens

    @staticmethod
    def _payload(request):
        body = {
            "source_code": _encode(request.source_code),
            "language_id": request.language_id,
            "stdin": _encode(request.stdin),
        }
        if request.cpu_time_limit is not None:
            body["cpu_time_limit"] = float(request.cpu_time_limit)
        if request.memory_limit is not None:
            body["memory_limit"] = int(request.memory_limit)
        return body

    def _wait(self, http, tokens):
        deadline = time.monotonic() + self.timeout_seconds
        done = {}
        while True:
            pending = [t for t in tokens if t not in done]
            for start in range(0, len(pending), BATCH_SIZE):
                chunk = pending[start : start + BATCH_SIZE]
                data = self._request(
                    http,
                    "GET",
                    "/submissions/batch",
                    params={
                        "tokens": ",".join(chunk),
                        "base64_encoded": "true",
                        "fields": "token,status,stdout,stderr,compile_output,message,time,memory",
                    },
                )
                for row in data.get("submissions", []):
                    if row and row.get("status", {}).get("id", 0) >= FINISHED_FROM:
                        done[row["token"]] = self._execution(row)
            if len(done) == len(tokens):
                return [done[t] for t in tokens]
            if time.monotonic() >= deadline:
                raise Judge0Error(f"Judge0 did not finish {len(tokens) - len(done)} runs in time.")
            self.sleep(self.poll_interval)

    @staticmethod
    def _execution(row):
        status = row.get("status") or {}
        return Execution(
            token=row["token"],
            status_id=status.get("id", STATUS_INTERNAL_ERROR),
            status=status.get("description", ""),
            stdout=_decode(row.get("stdout")),
            stderr=_decode(row.get("stderr")),
            compile_output=_decode(row.get("compile_output")),
            message=_decode(row.get("message")) if row.get("message") else "",
            time=float(row["time"]) if row.get("time") is not None else None,
            memory=int(row["memory"]) if row.get("memory") is not None else None,
        )


def get_client():
    """Factory used by the judging service; tests replace it."""
    return Judge0Client()
