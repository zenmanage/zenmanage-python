# Changelog

All notable changes to this project are documented in this file.

## Unreleased

- Fixed `Flag.as_string()` to return `""` for a `json`-typed flag instead of stringifying the decoded dict/list, matching the safe-zero-value behavior already used by `as_bool()`/`as_number()` and the documented cross-SDK coercion contract. (ZEN-1750)
- Fixed `single()` (sync and async) to fall back to the caller-provided default (inline value or `DefaultsCollection` entry) when the rules fetch fails outright, e.g. an invalid or unreachable environment key — previously the fetch error propagated to the caller instead of falling back, unlike the reference PHP SDK. (ZEN-1751)

## 1.2.0 - 2026-09-24

- Added the `json` flag type: `Flag.as_json()` returns the decoded value (a `dict` or `list`) for a `json`-typed flag. Like `as_bool()`/`as_string()`/`as_number()`, calling it on a flag of a different type returns a safe zero value (`{}`) rather than attempting a lossy conversion. `dict`/`list` default values passed to `single()` or `DefaultsCollection` are now typed as `json` instead of being stringified.

## 1.1.3 - 2026-09-23

- Fixed `single()`/`all()` (sync and async) to gracefully degrade a flag whose `type` this SDK release doesn't recognize (e.g. a future `json` flag type) instead of mis-parsing its value wrapper into garbage. `single()` now falls back to the caller's default (inline value or `DefaultsCollection` entry), matching the existing "flag not found" behavior, and `all()` skips the unrecognized flag while still returning every other flag unaffected. A warning is logged once per flag key via the configured logger. This was already tolerant of unrecognized types at the parsing layer (no exception was ever raised), but `as_string()`/`get_value()`/`as_number()` on an unrecognized-type flag previously returned a stringified/garbage representation of the raw value instead of the caller's default.

## 1.1.2 - 2026-08-16

- Renamed the `X-API-Key`, `X-ZENMANAGE-CONTEXT`, and `X-Default-Value` request headers to `X-ZEN-API-KEY`, `X-ZEN-CONTEXT`, and `X-ZEN-DEFAULT-VALUE`, matching the `X-ZEN-CLIENT-AGENT` header and the JavaScript/PHP SDKs.
- The `X-ZEN-CLIENT-AGENT` header now reports the installed package's actual version instead of a hardcoded constant that had drifted out of date (stuck at `1.0.0`).

## 1.1.1 - 2026-08-05

- Fixed `single()` (sync and async) to report the effective default value (inline parameter, falling back to a `DefaultsCollection` entry) on every usage report, including when the flag is found and evaluated normally — previously the default was only sent on the fallback paths.

## 1.1.0 - 2026-08-05

- `report_usage()` now threads the default value used on a flag-evaluation fallback through to the API, sent as an `X-Default-Value` header, so it can be persisted and shown on the flag detail page.

## 1.0.1 - 2026-05-31

- Updated PyPI classifier from `Development Status :: 4 - Beta` to `5 - Production/Stable`.
- Removed internal development and publishing notes from README.

## 1.0.0 - 2026-05-31

- Initial Python SDK implementation.
- Added ConfigBuilder, flag evaluation, context targeting, and deterministic percentage rollouts.
- Added cache backends: in-memory, filesystem, and null.
- Added comprehensive test suite with 90%+ coverage target.
- Added runnable examples and publishing guide.
