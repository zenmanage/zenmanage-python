"""HTTP API client for fetching rules and reporting usage."""

from __future__ import annotations

import json
import time
from typing import Optional, cast
from urllib.parse import quote

import requests

from .context import Context
from .errors import FetchRulesError, InvalidRulesError
from .types import FlagValue, Logger, RulesResponse

SDK_VERSION = "1.0.0"
CLIENT_AGENT = "zenmanage-python"
DEFAULT_API_ENDPOINT = "https://api.zenmanage.com"
RULES_PATH = "/v1/flag-json"
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 0.1
REQUEST_TIMEOUT_SECONDS = 10


class ApiClient:
    def __init__(
        self,
        environment_token: str,
        api_endpoint: str = DEFAULT_API_ENDPOINT,
        logger: Optional[Logger] = None,
        enable_usage_reporting: bool = True,
        session: Optional[requests.Session] = None,
    ) -> None:
        self.base_url = api_endpoint.rstrip("/")
        self.enable_usage_reporting = enable_usage_reporting
        self.logger = logger
        self.session = session or requests.Session()

        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-API-Key": environment_token,
            "X-ZEN-CLIENT-AGENT": f"{CLIENT_AGENT}/{SDK_VERSION}",
        }

    def get_rules(self) -> RulesResponse:
        last_error: Optional[Exception] = None

        for attempt in range(MAX_RETRIES):
            try:
                if attempt > 0:
                    delay = RETRY_DELAY_SECONDS * (2 ** (attempt - 1))
                    self._debug(
                        "Retrying rules request",
                        extra={"attempt": attempt + 1, "delay": delay},
                    )
                    time.sleep(delay)

                cdn_url = self._get_cdn_rules_url()
                response = self.session.get(
                    cdn_url,
                    headers={"Accept": "application/json"},
                    timeout=REQUEST_TIMEOUT_SECONDS,
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
                requests.RequestException,
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

    def report_usage(
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
            headers["X-ZENMANAGE-CONTEXT"] = json.dumps(context.to_dict())

        if default_value is not None:
            headers["X-Default-Value"] = json.dumps({key: default_value})

        url = f"{self.base_url}/v1/flags/{quote(key, safe='')}/usage"

        try:
            self.session.post(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
        except requests.RequestException as error:
            self._debug("Failed to report usage", extra={"key": key, "error": str(error)})

    def _get_cdn_rules_url(self) -> str:
        url = f"{self.base_url}{RULES_PATH}"
        response = self.session.get(url, headers=self.headers, timeout=REQUEST_TIMEOUT_SECONDS)

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

    def _is_valid_metadata_response(self, data: object) -> bool:
        if not isinstance(data, dict):
            return False

        payload = data.get("data")
        if not isinstance(payload, dict):
            return False

        return "cdn" in payload and "path" in payload

    def _is_valid_rules_response(self, data: object) -> bool:
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
