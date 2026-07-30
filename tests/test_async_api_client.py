from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

import httpx
import pytest

from zenmanage.async_api_client import AsyncApiClient
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


class FakeAsyncClient:
    def __init__(
        self,
        get_responses: list[FakeResponse],
        post_error: Optional[Exception] = None,
    ) -> None:
        self._get_responses = get_responses
        self.post_error = post_error
        self.last_post_headers: Optional[dict[str, str]] = None
        self.last_post_url: Optional[str] = None
        self.closed = False

    async def get(self, *args: object, **kwargs: object) -> FakeResponse:
        if not self._get_responses:
            raise httpx.HTTPError("no more responses")
        return self._get_responses.pop(0)

    async def post(self, *args: object, **kwargs: object) -> None:
        if args:
            self.last_post_url = str(args[0])
        headers = kwargs.get("headers")
        if isinstance(headers, dict):
            self.last_post_headers = headers
        if self.post_error:
            raise self.post_error

    async def aclose(self) -> None:
        self.closed = True


class DummyLogger:
    def debug(self, msg: object, *args: object, **kwargs: object) -> None:
        return None

    def warning(self, msg: object, *args: object, **kwargs: object) -> None:
        return None

    def info(self, msg: object, *args: object, **kwargs: object) -> None:
        return None

    def error(self, msg: object, *args: object, **kwargs: object) -> None:
        return None


@pytest.mark.asyncio
async def test_get_rules_success() -> None:
    client = FakeAsyncClient(
        [
            FakeResponse(200, {"data": {"cdn": "https://cdn.example.com", "path": "/rules.json"}}),
            FakeResponse(200, {"version": "1", "flags": []}),
        ]
    )

    api = AsyncApiClient("srv_test", client=client)
    data = await api.get_rules()
    assert data["version"] == "1"


@pytest.mark.asyncio
async def test_get_rules_failure_raises() -> None:
    client = FakeAsyncClient([FakeResponse(500, {"error": "bad"})])
    api = AsyncApiClient("srv_test", client=client, logger=DummyLogger())

    with pytest.raises(FetchRulesError):
        await api.get_rules()


@pytest.mark.asyncio
async def test_get_rules_invalid_metadata_raises() -> None:
    client = FakeAsyncClient([FakeResponse(200, {"data": {"foo": "bar"}})])
    api = AsyncApiClient("srv_test", client=client)

    with pytest.raises(FetchRulesError):
        await api.get_rules()


@pytest.mark.asyncio
async def test_get_rules_invalid_rules_payload_raises() -> None:
    client = FakeAsyncClient(
        [
            FakeResponse(200, {"data": {"cdn": "https://cdn.example.com", "path": "/rules.json"}}),
            FakeResponse(200, {"invalid": True}),
            FakeResponse(200, {"data": {"cdn": "https://cdn.example.com", "path": "/rules.json"}}),
            FakeResponse(200, {"invalid": True}),
            FakeResponse(200, {"data": {"cdn": "https://cdn.example.com", "path": "/rules.json"}}),
            FakeResponse(200, {"invalid": True}),
        ]
    )
    api = AsyncApiClient("srv_test", client=client)

    with pytest.raises(FetchRulesError):
        await api.get_rules()


@pytest.mark.asyncio
async def test_report_usage_with_context_header() -> None:
    client = FakeAsyncClient([])
    api = AsyncApiClient("srv_test", client=client)
    await api.report_usage("new-ui", Context.single("user", "u-1"))

    assert client.last_post_headers is not None
    assert "X-ZENMANAGE-CONTEXT" in client.last_post_headers


@pytest.mark.asyncio
async def test_report_usage_disabled() -> None:
    client = FakeAsyncClient([])
    api = AsyncApiClient("srv_test", client=client, enable_usage_reporting=False)
    await api.report_usage("new-ui")
    assert client.last_post_headers is None


@pytest.mark.asyncio
async def test_report_usage_anonymous_context_omits_header() -> None:
    client = FakeAsyncClient([])
    api = AsyncApiClient("srv_test", client=client)
    await api.report_usage("new-ui", Context("anonymous"))
    assert client.last_post_headers is not None
    assert "X-ZENMANAGE-CONTEXT" not in client.last_post_headers


@pytest.mark.asyncio
async def test_report_usage_network_error_is_ignored() -> None:
    client = FakeAsyncClient([], post_error=httpx.HTTPError("boom"))
    api = AsyncApiClient("srv_test", client=client)
    await api.report_usage("new-ui", Context.single("user", "u-1"))


@pytest.mark.asyncio
async def test_report_usage_sends_default_value_header() -> None:
    client = FakeAsyncClient([])
    api = AsyncApiClient("srv_test", client=client)
    await api.report_usage("new-ui", None, True)

    assert client.last_post_headers is not None
    assert json.loads(client.last_post_headers["X-Default-Value"]) == {"new-ui": True}


@pytest.mark.asyncio
async def test_report_usage_sends_non_bool_default_value_header() -> None:
    client = FakeAsyncClient([])
    api = AsyncApiClient("srv_test", client=client)
    await api.report_usage("num-flag", None, 42)

    assert client.last_post_headers is not None
    assert json.loads(client.last_post_headers["X-Default-Value"]) == {"num-flag": 42}


@pytest.mark.asyncio
async def test_report_usage_omits_default_value_header_when_not_provided() -> None:
    client = FakeAsyncClient([])
    api = AsyncApiClient("srv_test", client=client)
    await api.report_usage("new-ui")

    assert client.last_post_headers is not None
    assert "X-Default-Value" not in client.last_post_headers


@pytest.mark.asyncio
async def test_aclose_closes_client() -> None:
    client = FakeAsyncClient([])
    api = AsyncApiClient("srv_test", client=client)
    await api.aclose()
    assert client.closed


@pytest.mark.asyncio
async def test_get_rules_rejects_http_cdn_url() -> None:
    """CDN URL must be HTTPS to prevent SSRF."""
    http_cdn = FakeResponse(200, {"data": {"cdn": "http://internal-host", "path": "/rules.json"}})
    client = FakeAsyncClient([http_cdn, http_cdn, http_cdn])
    api = AsyncApiClient("srv_test", client=client)

    with pytest.raises(FetchRulesError, match="HTTPS"):
        await api.get_rules()


@pytest.mark.asyncio
async def test_report_usage_url_encodes_flag_key() -> None:
    """Flag keys with path-special characters must be percent-encoded in the URL."""
    client = FakeAsyncClient([])
    api = AsyncApiClient("srv_test", client=client)

    await api.report_usage("flag/with/slashes")

    assert client.last_post_url is not None
    assert "flag%2Fwith%2Fslashes" in client.last_post_url
    assert "/flag/with/slashes/" not in client.last_post_url
