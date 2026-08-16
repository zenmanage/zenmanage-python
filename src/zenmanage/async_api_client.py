"""Async HTTP API client for fetching rules and reporting usage."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Optional, cast
from urllib.parse import quote

import httpx

from ._version import SDK_VERSION
from .context import Context
from .errors import FetchRulesError, InvalidRulesError
from .types import FlagValue, Logger, RulesResponse

CLIENT_AGENT = "zenmanage-python"
DEFAULT_API_ENDPOINT = "https://api.zenmanage.com"
RULES_PATH = "/v1/flag-json"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 0.1
REQUEST_TIMEOUT_SECONDS = 10


class AsyncApiClient:
    def __init__(
        self,
        environment_token: str,
        api_endpoint: str = DEFAULT_API_ENDPOINT,
        logger: Optional[Logger] = None,
        enable_usage_reporting: bool = True,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.base_url = api_endpoint.rstrip("/")
        self.enable_usage_reporting = enable_usage_reporting
        self.logger = logger
        self.client = client or httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS)

        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-ZEN-API-KEY": environment_token,
            "X-ZEN-CLIENT-AGENT": f"{CLIENT_AGENT}/{SDK_VERSION}",
        }

    async def get_rules(self) -> RulesResponse:
        last_error: Optional[Exception] = None

        for attempt in range(MAX_RETRIES):
            try:
                if attempt > 0:
                    delay = RETRY_DELAY_SECONDS * (2 ** (attempt - 1))
                    self._debug(
                        "Retrying rules request",
                        extra={"attempt": attempt + 1, "delay": delay},
                    )
                    await asyncio.sleep(delay)

                cdn_url = await self._get_cdn_rules_url()
                response = await self.client.get(
                    cdn_url,
                    headers={"Accept": "application/json"},
                )
                if response.status_code >= 400:
                    raise FetchRulesError(
                        f"CDN request failed with status {response.status_code}",
                        response.status_code,
                    )

                data = response.json()
                if not self._is_valid_rules_response(data):
                    raise InvalidRulesError("Invalid response format from CDN")

                return cast(RulesResponse, data)
            except (
                httpx.HTTPError,
                ValueError,
                FetchRulesError,
                InvalidRulesError,
            ) as error:
                last_error = error
                self._warning(
                    "Failed to fetch rules",
                    extra={"attempt": attempt + 1, "error": str(error)},
                )

        raise FetchRulesError(f"Failed to fetch rules after {MAX_RETRIES} attempts: {last_error}")

    async def report_usage(
        self,
        key: str,
        context: Optional[Context] = None,
        default_value: Optional[FlagValue] = None,
    ) -> None:
        if not self.enable_usage_reporting:
            self._debug("Usage reporting disabled")
            return

        headers = dict(self.headers)
        if context is not None and self._should_send_context(context):
            headers["X-ZEN-CONTEXT"] = json.dumps(context.to_dict())

        if default_value is not None:
            try:
                headers["X-ZEN-DEFAULT-VALUE"] = json.dumps({key: default_value})
            except TypeError as error:
                self._debug(
                    "Failed to serialize default value",
                    extra={"key": key, "error": str(error)},
                )

        url = f"{self.base_url}/v1/flags/{quote(key, safe='')}/usage"

        try:
            await self.client.post(url, headers=headers)
        except httpx.HTTPError as error:
            self._debug("Failed to report usage", extra={"key": key, "error": str(error)})

    async def _get_cdn_rules_url(self) -> str:
        url = f"{self.base_url}{RULES_PATH}"
        response = await self.client.get(url, headers=self.headers)

        if response.status_code >= 400:
            raise FetchRulesError(
                f"API metadata request failed with status {response.status_code}",
                response.status_code,
            )

        try:
            metadata = response.json()
        except ValueError as error:
            raise InvalidRulesError("API response is not valid JSON") from error

        if not self._is_valid_metadata_response(metadata):
            raise InvalidRulesError("API response missing cdn or path fields")

        cdn = metadata["data"]["cdn"]
        path = metadata["data"]["path"]
        if not isinstance(cdn, str) or not isinstance(path, str):
            raise InvalidRulesError("cdn or path fields are not strings")

        if not cdn.startswith("https://"):
            raise InvalidRulesError("CDN URL must use HTTPS")

        return cdn + path

    async def aclose(self) -> None:
        await self.client.aclose()

    def _is_valid_metadata_response(self, data: Any) -> bool:
        if not isinstance(data, dict):
            return False

        payload = data.get("data")
        if not isinstance(payload, dict):
            return False

        return "cdn" in payload and "path" in payload

    def _is_valid_rules_response(self, data: Any) -> bool:
        if not isinstance(data, dict):
            return False
        return isinstance(data.get("version"), str) and isinstance(data.get("flags"), list)

    def _should_send_context(self, context: Context) -> bool:
        return not (
            context.type == "anonymous"
            and context.name is None
            and context.identifier is None
            and len(context.get_attributes()) == 0
        )

    def _debug(self, message: str, extra: Optional[dict[str, object]] = None) -> None:
        if self.logger is not None:
            self.logger.debug(message, extra=extra)

    def _warning(self, message: str, extra: Optional[dict[str, object]] = None) -> None:
        if self.logger is not None:
            self.logger.warning(message, extra=extra)
