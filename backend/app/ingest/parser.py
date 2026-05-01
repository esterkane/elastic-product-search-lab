from __future__ import annotations

import re
from dataclasses import dataclass, field


FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(?P<body>.*?)(?:\r?\n)---[ \t]*(?:\r?\n|$)", re.DOTALL)
HEADING_RE = re.compile(r"^(?P<level>#{1,6})[ \t]+(?P<title>.+?)[ \t]*#*[ \t]*$", re.MULTILINE)
ANCHOR_RE = re.compile(r"[^a-z0-9 -]")
WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class Heading:
    level: int
    title: str
    anchor: str
    line_number: int


@dataclass(frozen=True)
class ParsedDocument:
    content: str
    frontmatter: dict[str, object] = field(default_factory=dict)
    headings: list[Heading] = field(default_factory=list)


def parse_frontmatter(markdown: str) -> tuple[dict[str, object], str]:
    match = FRONTMATTER_RE.match(markdown)
    if not match:
        return {}, markdown

    frontmatter = parse_simple_yaml(match.group("body"))
    return frontmatter, markdown[match.end() :]


def parse_simple_yaml(text: str) -> dict[str, object]:
    values: dict[str, object] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, raw_value = line.split(":", maxsplit=1)
        key = key.strip()
        value = raw_value.strip()
        if not key:
            continue
        values[key] = parse_scalar(value)
    return values


def parse_scalar(value: str) -> object:
    if not value:
        return ""
    if value[0:1] in {"'", '"'} and value[-1:] == value[0]:
        return value[1:-1]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [str(parse_scalar(part.strip())) for part in inner.split(",")]
    return value


def stable_anchor(title: str) -> str:
    normalized = title.strip().lower()
    normalized = ANCHOR_RE.sub("", normalized)
    normalized = WHITESPACE_RE.sub("-", normalized)
    normalized = re.sub("-+", "-", normalized).strip("-")
    return normalized or "section"


def extract_headings(markdown: str) -> list[Heading]:
    headings: list[Heading] = []
    seen: dict[str, int] = {}
    for match in HEADING_RE.finditer(markdown):
        title = match.group("title").strip()
        base_anchor = stable_anchor(title)
        ordinal = seen.get(base_anchor, 0)
        seen[base_anchor] = ordinal + 1
        anchor = base_anchor if ordinal == 0 else f"{base_anchor}-{ordinal}"
        line_number = markdown.count("\n", 0, match.start()) + 1
        headings.append(Heading(level=len(match.group("level")), title=title, anchor=anchor, line_number=line_number))
    return headings


def parse_markdown(markdown: str) -> ParsedDocument:
    frontmatter, content = parse_frontmatter(markdown)
    return ParsedDocument(content=content, frontmatter=frontmatter, headings=extract_headings(content))


def classify_content_type(repo: str, path: str) -> str:
    lowered = path.replace("\\", "/").lower()
    if repo.endswith("/docs-content"):
        if lowered.startswith("release-notes/") or "/release-notes/" in lowered:
            return "release_note"
        if lowered.startswith("troubleshoot/") or "/troubleshoot/" in lowered:
            return "troubleshooting"
        if lowered.startswith("reference/") or "/reference/" in lowered:
            return "reference"
        if lowered.startswith("get-started/") or "/get-started/" in lowered:
            return "guide"
        return "documentation"
    if repo.endswith("/docs-builder") or repo.endswith("/docs"):
        return "tooling"
    if repo.endswith("/elasticsearch-labs"):
        if lowered.startswith("example-apps/") or "/example-apps/" in lowered:
            return "example"
        return "lab"
    if repo.endswith("/labs-releases"):
        return "release_metadata"
    return "documentation"

