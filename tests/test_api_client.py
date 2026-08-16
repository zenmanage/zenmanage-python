from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

import pytest
import requests

from zenmanage._version import SDK_VERSION
from zenmanage.api_client import ApiClient
from zenmanage.context import Context
from zenmanage.errors import FetchRulesError


@dataclass
class FakeResponse:
    status_code: int
    payload: object

    def json(self) -> object:
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class FakeSession:
    def __init__(
        self,
        get_responses: list[FakeResponse],
        post_error: Optional[Exception] = None,
    ) -> None:
        self._get_responses = get_responses
        self.post_error = post_error
        self.last_post_headers: Optional[dict[str, str]] = None
        self.last_post_url: Optional[str] = None

    def get(self, *args: object, **kwargs: object) -> FakeResponse:
        if not self._get_responses:
            raise requests.RequestException("no more responses")
        return self._get_responses.pop(0)

    def post(self, *args: object, **kwargs: object) -> None:
        if args:
            self.last_post_url = str(args[0])
        headers = kwargs.get("headers")
        if isinstance(headers, dict):
            self.last_post_headers = headers
        if self.post_error:
            raise self.post_error


class DummyLogger:
    def debug(self, msg: object, *args: object, **kwargs: object) -> None:
        return None

    def warning(self, msg: object, *args: object, **kwargs: object) -> None:
        return None

    def info(self, msg: object, *args: object, **kwargs: object) -> None:
        return None

    def error(self, msg: object, *args: object, **kwargs: object) -> None:
        return None


def test_client_agent_header_uses_installed_package_version() -> None:
    session = FakeSession([])
    client = ApiClient("srv_test", session=session)

    assert client.headers["X-ZEN-CLIENT-AGENT"] == f"zenmanage-python/{SDK_VERSION}"


def test_get_rules_success() -> None:
    session = FakeSession(
        [
            FakeResponse(200, {"data": {"cdn": "https://cdn.example.com", "path": "/rules.json"}}),
            FakeResponse(200, {"version": "1", "flags": []}),
        ]
    )

    client = ApiClient("srv_test", session=session)
    data = client.get_rules()
    assert data["version"] == "1"


def test_get_rules_invalid_metadata() -> None:
    session = FakeSession([FakeResponse(200, {"data": {"foo": "bar"}})])
    client = ApiClient("srv_test", session=session)

    with pytest.raises(FetchRulesError):
        client.get_rules()


def test_get_rules_invalid_rules_payload() -> None:
    session = FakeSession(
        [
            FakeResponse(200, {"data": {"cdn": "https://cdn.example.com", "path": "/rules.json"}}),
            FakeResponse(200, {"wrong": "shape"}),
            FakeResponse(200, {"data": {"cdn": "https://cdn.example.com", "path": "/rules.json"}}),
            FakeResponse(200, {"wrong": "shape"}),
            FakeResponse(200, {"data": {"cdn": "https://cdn.example.com", "path": "/rules.json"}}),
            FakeResponse(200, {"wrong": "shape"}),
        ]
    )
    client = ApiClient("srv_test", session=session)

    with pytest.raises(FetchRulesError):
        client.get_rules()


def test_get_rules_metadata_http_error() -> None:
    session = FakeSession([FakeResponse(500, {"error": "x"})])
    client = ApiClient("srv_test", session=session, logger=DummyLogger())

    with pytest.raises(FetchRulesError):
        client.get_rules()


def test_get_rules_invalid_metadata_json() -> None:
    session = FakeSession([FakeResponse(200, ValueError("bad json"))])
    client = ApiClient("srv_test", session=session)

    with pytest.raises(FetchRulesError):
        client.get_rules()


def test_report_usage_with_context_header() -> None:
    session = FakeSession([], post_error=None)
    client = ApiClient("srv_test", session=session)

    context = Context.single("user", "user-1")
    client.report_usage("new-ui", context)

    assert session.last_post_headers is not None
    assert "X-ZEN-CONTEXT" in session.last_post_headers


def test_report_usage_without_context_header_for_anonymous() -> None:
    session = FakeSession([], post_error=None)
    client = ApiClient("srv_test", session=session)

    client.report_usage("new-ui", Context("anonymous"))

    assert session.last_post_headers is not None
    assert "X-ZEN-CONTEXT" not in session.last_post_headers


def test_report_usage_disabled() -> None:
    session = FakeSession([])
    client = ApiClient("srv_test", session=session, enable_usage_reporting=False)
    client.report_usage("new-ui", Context.single("user", "u-1"))
    assert session.last_post_headers is None


def test_report_usage_ignores_errors() -> None:
    session = FakeSession([], post_error=requests.RequestException("boom"))
    client = ApiClient("srv_test", session=session)

    # no exception
    client.report_usage("new-ui")


def test_get_rules_rejects_http_cdn_url() -> None:
    """CDN URL must be HTTPS to prevent SSRF."""
    http_cdn = FakeResponse(200, {"data": {"cdn": "http://internal-host", "path": "/rules.json"}})
    session = FakeSession([http_cdn, http_cdn, http_cdn])
    client = ApiClient("srv_test", session=session)

    with pytest.raises(FetchRulesError, match="HTTPS"):
        client.get_rules()


def test_report_usage_sends_default_value_header() -> None:
    session = FakeSession([])
    client = ApiClient("srv_test", session=session)

    client.report_usage("new-ui", None, True)

    assert session.last_post_headers is not None
    assert json.loads(session.last_post_headers["X-ZEN-DEFAULT-VALUE"]) == {"new-ui": True}


def test_report_usage_sends_non_bool_default_value_header() -> None:
    session = FakeSession([])
    client = ApiClient("srv_test", session=session)

    client.report_usage("num-flag", None, 42)

    assert session.last_post_headers is not None
    assert json.loads(session.last_post_headers["X-ZEN-DEFAULT-VALUE"]) == {"num-flag": 42}


def test_report_usage_omits_default_value_header_when_not_provided() -> None:
    session = FakeSession([])
    client = ApiClient("srv_test", session=session)

    client.report_usage("new-ui")

    assert session.last_post_headers is not None
    assert "X-ZEN-DEFAULT-VALUE" not in session.last_post_headers


def test_report_usage_skips_default_value_header_on_serialization_failure() -> None:
    session = FakeSession([])
    client = ApiClient("srv_test", session=session, logger=DummyLogger())

    # object() is not JSON-serializable; the header should be dropped, not raise.
    client.report_usage("new-ui", None, object())  # type: ignore[arg-type]

    assert session.last_post_headers is not None
    assert "X-ZEN-DEFAULT-VALUE" not in session.last_post_headers


def test_report_usage_url_encodes_flag_key() -> None:
    """Flag keys with path-special characters must be percent-encoded in the URL."""
    session = FakeSession([])
    client = ApiClient("srv_test", session=session)

    client.report_usage("flag/with/slashes")

    assert session.last_post_url is not None
    assert "flag%2Fwith%2Fslashes" in session.last_post_url
    assert "/flag/with/slashes/" not in session.last_post_url
