#!/usr/bin/env python3
"""Validate release metadata consistency for tag-driven publishing.

Checks:
- project.version in pyproject.toml
- corresponding changelog heading in CHANGELOG.md
- optional git tag (vX.Y.Z) matches project.version
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


def extract_project_version(pyproject_path: Path) -> str:
    content = pyproject_path.read_text(encoding="utf-8")

    in_project = False
    for raw_line in content.splitlines():
        line = raw_line.strip()

        if line.startswith("[") and line.endswith("]"):
            in_project = line == "[project]"
            continue

        if in_project:
            match = re.match(r'^version\s*=\s*"([^"]+)"\s*$', line)
            if match:
                return match.group(1)

    raise ValueError("Unable to find [project].version in pyproject.toml")


def changelog_has_version(changelog_path: Path, version: str) -> bool:
    content = changelog_path.read_text(encoding="utf-8")
    pattern = re.compile(rf"^##\s+{re.escape(version)}\s+-\s+", re.MULTILINE)
    return bool(pattern.search(content))


def normalize_tag(tag: str) -> str:
    return tag[1:] if tag.startswith("v") else tag


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate release metadata")
    parser.add_argument("--tag", help="Release tag, usually vX.Y.Z", default=None)
    parser.add_argument(
        "--pyproject",
        default="pyproject.toml",
        help="Path to pyproject.toml",
    )
    parser.add_argument(
        "--changelog",
        default="CHANGELOG.md",
        help="Path to changelog file",
    )
    args = parser.parse_args()

    pyproject_path = Path(args.pyproject)
    changelog_path = Path(args.changelog)

    if not pyproject_path.exists():
        print(f"ERROR: {pyproject_path} not found")
        return 1

    if not changelog_path.exists():
        print(f"ERROR: {changelog_path} not found")
        return 1

    version = extract_project_version(pyproject_path)
    print(f"Detected project version: {version}")

    if not changelog_has_version(changelog_path, version):
        print(f"ERROR: Missing changelog section for version {version}")
        print("Expected heading format: ## <version> - YYYY-MM-DD")
        return 1

    print("Changelog contains current version heading")

    if args.tag:
        normalized_tag = normalize_tag(args.tag)
        if normalized_tag != version:
            print(
                "ERROR: Tag/version mismatch: "
                f"tag={args.tag} maps to {normalized_tag}, "
                f"pyproject version={version}"
            )
            return 1

        print(f"Tag matches project version: {args.tag}")

    print("Release metadata validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
