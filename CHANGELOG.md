# Changelog

All notable changes to this project are documented in this file.

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
