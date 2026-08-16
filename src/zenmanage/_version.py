"""SDK version, sourced from installed package metadata."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    SDK_VERSION = version("zenmanage")
except PackageNotFoundError:
    SDK_VERSION = "0.0.0"
