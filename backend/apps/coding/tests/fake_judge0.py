"""In-memory stand-in for the Judge0 REST API, for tests.

"Programs" are keywords in the source code:
    SUM            print the sum of the integers on stdin
    WRONG          print 0
    COMPILE_ERROR  compilation fails
    TLE            time limit exceeded
    CRASH          runtime error (NZEC)
    SLOW_SUM       like SUM but reports 0.9s
Every submission reports "Processing" on its first poll, then the final result.
"""

import base64
import json
import uuid
from urllib.parse import parse_qs

import httpx


def b64(text):
    return base64.b64encode(text.encode()).decode() if text is not None else None


def unb64(text):
    return base64.b64decode(text).decode() if text else ""


class FakeJudge0:
    def __init__(self, token="test-token", batch_limit=20):
        self.token = token
        self.batch_limit = batch_limit
        self.submissions = {}
        self.polls = {}
        self.batch_posts = 0
        self.last_request_bodies = []

    # ---- program semantics
    def _run(self, source, stdin):
        if "COMPILE_ERROR" in source:
            return {
                "status": {"id": 6, "description": "Compilation Error"},
                "compile_output": "main.c:1: error",
            }
        if "TLE" in source:
            return {"status": {"id": 5, "description": "Time Limit Exceeded"}, "time": "2.0"}
        if "CRASH" in source:
            return {
                "status": {"id": 11, "description": "Runtime Error (NZEC)"},
                "stderr": "Traceback",
            }
        if "WRONG" in source:
            out = "0\n"
        else:
            out = f"{sum(int(x) for x in stdin.split())}\n"
        time = "0.9" if "SLOW" in source else "0.01"
        return {
            "status": {"id": 3, "description": "Accepted"},
            "stdout": out,
            "time": time,
            "memory": 3200,
        }

    # ---- transport
    def handler(self, request: httpx.Request) -> httpx.Response:
        if self.token and request.headers.get("X-Auth-Token") != self.token:
            return httpx.Response(401, json={"error": "Authentication failed."})
        path = request.url.path
        if request.method == "GET" and path == "/languages":
            return httpx.Response(
                200,
                json=[{"id": 71, "name": "Python (3.8.1)"}, {"id": 54, "name": "C++ (GCC 9.2.0)"}],
            )
        if request.method == "POST" and path == "/submissions/batch":
            self.batch_posts += 1
            body = json.loads(request.content)
            self.last_request_bodies.append(body)
            items = body["submissions"]
            if len(items) > self.batch_limit:
                return httpx.Response(422, json={"error": "batch too large"})
            out = []
            for item in items:
                token = uuid.uuid4().hex
                self.submissions[token] = self._run(
                    unb64(item["source_code"]), unb64(item.get("stdin"))
                )
                self.polls[token] = 0
                out.append({"token": token})
            return httpx.Response(201, json=out)
        if request.method == "GET" and path == "/submissions/batch":
            tokens = parse_qs(request.url.query.decode())["tokens"][0].split(",")
            rows = []
            for token in tokens:
                self.polls[token] += 1
                if self.polls[token] == 1:
                    rows.append({"token": token, "status": {"id": 2, "description": "Processing"}})
                    continue
                result = self.submissions[token]
                rows.append(
                    {
                        "token": token,
                        "status": result["status"],
                        "stdout": b64(result.get("stdout")),
                        "stderr": b64(result.get("stderr")),
                        "compile_output": b64(result.get("compile_output")),
                        "message": None,
                        "time": result.get("time"),
                        "memory": result.get("memory"),
                    }
                )
            return httpx.Response(200, json={"submissions": rows})
        return httpx.Response(404, json={"error": "not found"})

    def transport(self):
        return httpx.MockTransport(self.handler)
