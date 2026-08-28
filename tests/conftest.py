"""Shared fixtures: a fake WeFact backend behind httpx.MockTransport.

No network. Each test gets a `wefact` fake that records every request
(decoded form fields) and answers from a queue of canned responses.
"""

from __future__ import annotations

import json
from urllib.parse import parse_qsl

import httpx
import pytest

from wefact_mcp import server
from wefact_mcp.client import WeFactClient


def ok(controller: str, action: str, **payload) -> dict:
    return {"controller": controller, "action": action, "status": "success",
            "date": "2026-08-28T10:00:00+02:00", **payload}


def err(controller: str, action: str, *errors: str) -> dict:
    return {"controller": controller, "action": action, "status": "error",
            "date": "2026-08-28T10:00:00+02:00", "errors": list(errors)}


class FakeWeFact:
    def __init__(self) -> None:
        self.requests: list[dict[str, str]] = []
        self.responses: list[httpx.Response] = []

    def queue(self, body, status_code: int = 200) -> None:
        if isinstance(body, (dict, list)):
            self.responses.append(httpx.Response(status_code, json=body))
        else:
            self.responses.append(httpx.Response(status_code, text=body))

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(dict(parse_qsl(request.content.decode(), keep_blank_values=True)))
        if not self.responses:
            raise AssertionError("no queued response for " + json.dumps(self.requests[-1]))
        return self.responses.pop(0)

    @property
    def last(self) -> dict[str, str]:
        return self.requests[-1]


@pytest.fixture
def wefact(monkeypatch) -> FakeWeFact:
    fake = FakeWeFact()
    client = WeFactClient(
        "test-key",
        transport=httpx.MockTransport(fake.handler),
        sleep=lambda _: None,  # no real backoff delays in tests
    )
    monkeypatch.setattr(server, "_client", client)
    yield fake
    client.close()
