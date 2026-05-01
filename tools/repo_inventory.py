#!/usr/bin/env python3
"""Clone/update selected Elastic repos and emit inventory manifests."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


REPOS: tuple[str, ...] = (
    "https://github.com/elastic/docs-content.git",
    "https://github.com/elastic/docs-builder.git",
    "https://github.com/elastic/docs.git",
    "https://github.com/elastic/elasticsearch-labs.git",
    "https://github.com/elastic/labs-releases.git",
)

KEY_CONFIG_NAMES: frozenset[str] = frozenset(
    {
        ".editorconfig",
        ".env.example",
        ".gitignore",
        ".markdownlint.json",
        ".markdownlint.yml",
        ".pre-commit-config.yaml",
        ".prettierrc",
        ".prettierrc.json",
        ".prettierrc.yml",
        "Dockerfile",
        "Makefile",
        "compose.yaml",
        "docker-compose.yml",
        "package-lock.json",
        "package.json",
        "pnpm-lock.yaml",
        "pyproject.toml",
        "requirements.txt",
        "tsconfig.json",
        "yarn.lock",
    }
)

README_NAMES: frozenset[str] = frozenset({"README", "README.md", "README.asciidoc", "README.adoc", "README.rst"})
CONTRIBUTING_NAMES: frozenset[str] = frozenset(
    {"CONTRIBUTING", "CONTRIBUTING.md", "CONTRIBUTING.asciidoc", "CONTRIBUTING.adoc", "CONTRIBUTING.rst"}
)
CODEOWNERS_NAMES: frozenset[str] = frozenset({"CODEOWNERS"})
LICENSE_PREFIXES: tuple[str, ...] = ("LICENSE", "LICENCE", "COPYING", "NOTICE")


@dataclass(frozen=True)
class GitResult:
    ok: bool
    command: tuple[str, ...]
    message: str = ""


def repo_slug(url: str) -> str:
    """Return owner/name for a GitHub URL."""
    stem = url.removesuffix(".git").rstrip("/")
    parts = stem.split("/")
    if len(parts) < 2:
        raise ValueError(f"Cannot derive repo slug from URL: {url}")
    return "/".join(parts[-2:])


def local_repo_name(url: str) -> str:
    return repo_slug(url).split("/", maxsplit=1)[1]


def run_git(args: Sequence[str], cwd: Path | None = None) -> GitResult:
    command = ("git", *args)
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        return GitResult(False, command, str(exc))

    if completed.returncode == 0:
        return GitResult(True, command, completed.stdout.strip())

    message = completed.stderr.strip() or completed.stdout.strip()
    return GitResult(False, command, message)


def clone_or_update(url: str, sources_dir: Path, skip_update: bool = False) -> GitResult:
    sources_dir.mkdir(parents=True, exist_ok=True)
    target = sources_dir / local_repo_name(url)

    if not target.exists():
        return run_git(("clone", "--", url, str(target)))

    if not (target / ".git").exists():
        return GitResult(False, ("git", "clone", "--", url, str(target)), f"{target} exists but is not a Git repo")

    if skip_update:
        return GitResult(True, ("git", "fetch", "--all", "--prune"), "update skipped")

    fetch_result = run_git(("fetch", "--all", "--prune"), cwd=target)
    if not fetch_result.ok:
        return fetch_result

    pull_result = run_git(("pull", "--ff-only"), cwd=target)
    if not pull_result.ok:
        return pull_result

    return pull_result


def git_output(args: Sequence[str], cwd: Path) -> str | None:
    result = run_git(args, cwd=cwd)
    return result.message if result.ok else None


def default_branch(repo_dir: Path) -> str | None:
    head_path = repo_dir / ".git" / "HEAD"
    try:
        head = head_path.read_text(encoding="utf-8").strip()
    except OSError:
        head = ""

    if head.startswith("ref: refs/heads/"):
        return head.removeprefix("ref: refs/heads/")

    origin_head = git_output(("symbolic-ref", "--short", "refs/remotes/origin/HEAD"), cwd=repo_dir)
    if origin_head:
        return origin_head.removeprefix("origin/")

    branch = git_output(("branch", "--show-current"), cwd=repo_dir)
    return branch or None


def relative_path(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def sorted_relative(paths: Iterable[Path], root: Path) -> list[str]:
    return sorted(relative_path(path, root) for path in paths)


def discover_top_level_dirs(repo_dir: Path) -> list[str]:
    return sorted(
        path.name
        for path in repo_dir.iterdir()
        if path.is_dir() and path.name != ".git"
    )


def discover_key_config_files(repo_dir: Path) -> list[str]:
    matches: list[Path] = []
    for path in repo_dir.iterdir():
        if path.is_file() and path.name in KEY_CONFIG_NAMES:
            matches.append(path)
    return sorted_relative(matches, repo_dir)


def discover_license_files(repo_dir: Path) -> list[str]:
    matches: list[Path] = []
    for path in repo_dir.iterdir():
        upper_name = path.name.upper()
        if path.is_file() and any(upper_name == prefix or upper_name.startswith(f"{prefix}.") for prefix in LICENSE_PREFIXES):
            matches.append(path)
    return sorted_relative(matches, repo_dir)


def first_license_file(repo_dir: Path) -> str | None:
    licenses = discover_license_files(repo_dir)
    if not licenses:
        return None

    exact = [name for name in licenses if name.upper() in {"LICENSE", "LICENCE"}]
    return exact[0] if exact else licenses[0]


def discover_named_files(repo_dir: Path, names: frozenset[str]) -> list[str]:
    matches: list[Path] = []
    for path in repo_dir.rglob("*"):
        if ".git" in path.parts:
            continue
        if path.is_file() and path.name in names:
            matches.append(path)
    return sorted_relative(matches, repo_dir)


def discover_workflows(repo_dir: Path) -> list[str]:
    workflows_dir = repo_dir / ".github" / "workflows"
    if not workflows_dir.is_dir():
        return []

    return sorted_relative((path for path in workflows_dir.rglob("*") if path.is_file()), repo_dir)


def inventory_repo(url: str, sources_dir: Path, git_result: GitResult | None = None) -> dict[str, object]:
    repo_dir = sources_dir / local_repo_name(url)
    slug = repo_slug(url)
    item: dict[str, object] = {
        "repo": slug,
        "url": url,
        "path": repo_dir.as_posix(),
        "default_branch": None,
        "license_file": None,
        "license_files": [],
        "top_level_dirs": [],
        "key_config_files": [],
        "readme_files": [],
        "contributing_files": [],
        "codeowners_files": [],
        "workflow_locations": [],
        "errors": [],
    }

    errors: list[str] = []
    if git_result and not git_result.ok:
        errors.append(f"{' '.join(git_result.command)}: {git_result.message}")

    if not repo_dir.is_dir():
        errors.append(f"Repository directory not found: {repo_dir}")
        item["errors"] = errors
        return item

    try:
        item.update(
            {
                "default_branch": default_branch(repo_dir),
                "license_file": first_license_file(repo_dir),
                "license_files": discover_license_files(repo_dir),
                "top_level_dirs": discover_top_level_dirs(repo_dir),
                "key_config_files": discover_key_config_files(repo_dir),
                "readme_files": discover_named_files(repo_dir, README_NAMES),
                "contributing_files": discover_named_files(repo_dir, CONTRIBUTING_NAMES),
                "codeowners_files": discover_named_files(repo_dir, CODEOWNERS_NAMES),
                "workflow_locations": discover_workflows(repo_dir),
            }
        )
    except OSError as exc:
        errors.append(str(exc))

    item["errors"] = errors
    return item


def write_json_manifest(manifest: dict[str, object], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def markdown_list(values: object) -> str:
    if not isinstance(values, list) or not values:
        return "_None found_"
    return "\n".join(f"- `{value}`" for value in values)


def write_markdown_manifest(manifest: dict[str, object], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    repos = manifest.get("repositories", [])
    lines = ["# Repository Manifest", ""]

    if isinstance(repos, list):
        for repo in repos:
            if not isinstance(repo, dict):
                continue
            lines.extend(
                [
                    f"## {repo.get('repo', 'unknown')}",
                    "",
                    f"- Default branch: `{repo.get('default_branch') or 'unknown'}`",
                    f"- License file: `{repo.get('license_file') or 'none found'}`",
                    "",
                    "### Top-level directories",
                    markdown_list(repo.get("top_level_dirs")),
                    "",
                    "### Key config files",
                    markdown_list(repo.get("key_config_files")),
                    "",
                    "### Project files",
                    markdown_list(
                        [
                            *repo.get("readme_files", []),
                            *repo.get("contributing_files", []),
                            *repo.get("codeowners_files", []),
                        ]
                    ),
                    "",
                    "### Workflows",
                    markdown_list(repo.get("workflow_locations")),
                    "",
                ]
            )
            errors = repo.get("errors")
            if isinstance(errors, list) and errors:
                lines.extend(["### Errors", markdown_list(errors), ""])

    output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def build_manifest(repo_urls: Sequence[str], sources_dir: Path, skip_update: bool = False) -> dict[str, object]:
    repositories: list[dict[str, object]] = []
    for url in repo_urls:
        git_result = clone_or_update(url, sources_dir, skip_update=skip_update)
        repositories.append(inventory_repo(url, sources_dir, git_result))

    return {
        "repositories": repositories,
        "repo_count": len(repositories),
    }


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources-dir", type=Path, default=Path("sources"), help="Directory for cloned repositories")
    parser.add_argument("--artifacts-dir", type=Path, default=Path("artifacts"), help="Directory for generated manifests")
    parser.add_argument("--skip-update", action="store_true", help="Inventory existing local repos without fetching")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    manifest = build_manifest(REPOS, args.sources_dir, skip_update=args.skip_update)

    json_path = args.artifacts_dir / "repo-manifest.json"
    markdown_path = args.artifacts_dir / "repo-manifest.md"
    write_json_manifest(manifest, json_path)
    write_markdown_manifest(manifest, markdown_path)

    errored = [
        repo.get("repo", "unknown")
        for repo in manifest["repositories"]
        if isinstance(repo, dict) and repo.get("errors")
    ]
    if errored:
        print(f"Wrote manifests with errors for: {', '.join(str(repo) for repo in errored)}", file=sys.stderr)
        return 1

    print(f"Wrote {json_path} and {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
