from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from backend.app.ingest.license import license_family_for_repo
from backend.app.ingest.parser import Heading, classify_content_type, parse_markdown, stable_anchor


@dataclass(frozen=True)
class SourceMetadata:
    repo: str
    repo_url: str
    path: str
    source_url: str
    commit_sha: str
    default_branch: str | None = None


@dataclass(frozen=True)
class DocumentRecord:
    repo: str
    repo_url: str
    path: str
    source_url: str
    commit_sha: str
    default_branch: str | None
    title: str | None
    content_type: str
    license_family: str
    frontmatter_json: str


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    repo: str
    path: str
    anchor: str
    heading: str | None
    chunk_index: int
    content: str
    source_url: str
    commit_sha: str
    content_type: str
    license_family: str


@dataclass(frozen=True)
class IngestedDocument:
    document: DocumentRecord
    chunks: list[ChunkRecord]


def make_chunk_id(repo: str, path: str, anchor: str, chunk_index: int) -> str:
    return hashlib.sha256(f"{repo}:{path}:{anchor}:{chunk_index}".encode()).hexdigest()


def build_source_url(repo_url: str, commit_sha: str, path: str, anchor: str | None = None) -> str:
    normalized_repo = repo_url.removesuffix(".git").rstrip("/")
    normalized_path = path.replace("\\", "/")
    url = f"{normalized_repo}/blob/{commit_sha}/{normalized_path}"
    return f"{url}#{anchor}" if anchor else url


def split_markdown_sections(content: str, headings: list[Heading]) -> list[tuple[str, str | None, str]]:
    if not headings:
        return [("document", None, content.strip())] if content.strip() else []

    sections: list[tuple[str, str | None, str]] = []
    lines = content.splitlines()
    heading_positions = [(heading, heading.line_number - 1) for heading in headings]

    preface = "\n".join(lines[: heading_positions[0][1]]).strip()
    if preface:
        sections.append(("document", None, preface))

    for index, (heading, start_line) in enumerate(heading_positions):
        end_line = heading_positions[index + 1][1] if index + 1 < len(heading_positions) else len(lines)
        section = "\n".join(lines[start_line:end_line]).strip()
        if section:
            sections.append((heading.anchor, heading.title, section))
    return sections


def split_text(text: str, max_chars: int) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []

    paragraphs = [paragraph.strip() for paragraph in stripped.split("\n\n") if paragraph.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
        current = paragraph

        while len(current) > max_chars:
            chunks.append(current[:max_chars].rstrip())
            current = current[max_chars:].lstrip()

    if current:
        chunks.append(current)
    return chunks


def ingest_markdown(markdown: str, metadata: SourceMetadata, max_chars: int = 1200) -> IngestedDocument:
    parsed = parse_markdown(markdown)
    content_type = classify_content_type(metadata.repo, metadata.path)
    license_family = license_family_for_repo(metadata.repo)
    title_value = parsed.frontmatter.get("title")
    title = str(title_value or (parsed.headings[0].title if parsed.headings else "")) or None

    document = DocumentRecord(
        repo=metadata.repo,
        repo_url=metadata.repo_url,
        path=metadata.path,
        source_url=metadata.source_url,
        commit_sha=metadata.commit_sha,
        default_branch=metadata.default_branch,
        title=title,
        content_type=content_type,
        license_family=license_family,
        frontmatter_json=json.dumps(parsed.frontmatter, sort_keys=True),
    )

    chunk_records: list[ChunkRecord] = []
    for anchor, heading, section in split_markdown_sections(parsed.content, parsed.headings):
        for chunk_index, chunk_text in enumerate(split_text(section, max_chars=max_chars)):
            chunk_records.append(
                ChunkRecord(
                    chunk_id=make_chunk_id(metadata.repo, metadata.path, anchor, chunk_index),
                    repo=metadata.repo,
                    path=metadata.path,
                    anchor=anchor,
                    heading=heading,
                    chunk_index=chunk_index,
                    content=chunk_text,
                    source_url=build_source_url(metadata.repo_url, metadata.commit_sha, metadata.path, anchor),
                    commit_sha=metadata.commit_sha,
                    content_type=content_type,
                    license_family=license_family,
                )
            )

    return IngestedDocument(document=document, chunks=chunk_records)
