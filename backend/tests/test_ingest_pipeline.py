import hashlib

from backend.app.ingest.chunker import SourceMetadata, ingest_markdown, make_chunk_id
from backend.app.ingest.license import license_family_for_repo
from backend.app.ingest.parser import classify_content_type, extract_headings, parse_markdown
from backend.app.models import Base, Chunk, Document, EvidenceLink, Recommendation


def test_sqlalchemy_models_define_expected_tables() -> None:
    assert {"documents", "chunks", "evidence_links", "recommendations"}.issubset(Base.metadata.tables)
    assert Document.__tablename__ == "documents"
    assert Chunk.__tablename__ == "chunks"
    assert EvidenceLink.__tablename__ == "evidence_links"
    assert Recommendation.__tablename__ == "recommendations"


def test_parse_frontmatter_and_extract_headings_with_stable_duplicate_anchors() -> None:
    parsed = parse_markdown(
        """---
title: Search guide
canonical: true
tags: [search, docs]
---
# Search

Intro.

## Install & Configure

Steps.

## Install Configure

More steps.
"""
    )

    assert parsed.frontmatter == {"canonical": True, "tags": ["search", "docs"], "title": "Search guide"}
    assert [(heading.level, heading.title, heading.anchor) for heading in parsed.headings] == [
        (1, "Search", "search"),
        (2, "Install & Configure", "install-configure"),
        (2, "Install Configure", "install-configure-1"),
    ]


def test_heading_extraction_ignores_frontmatter_after_parse() -> None:
    parsed = parse_markdown("---\ntitle: Not a # heading\n---\n# Real Heading\n")

    assert extract_headings(parsed.content)[0].anchor == "real-heading"


def test_chunking_records_canonical_metadata_and_license() -> None:
    metadata = SourceMetadata(
        repo="elastic/docs-content",
        repo_url="https://github.com/elastic/docs-content.git",
        path="troubleshoot/search/fix-results.md",
        source_url="https://github.com/elastic/docs-content/blob/abc123/troubleshoot/search/fix-results.md",
        commit_sha="abc123",
        default_branch="main",
    )
    ingested = ingest_markdown(
        """---
title: Fix search results
---
# Fix search results

First paragraph.

Second paragraph.

## Verify

Run a query.
        """,
        metadata,
        max_chars=50,
    )

    assert ingested.document.title == "Fix search results"
    assert ingested.document.content_type == "troubleshooting"
    assert ingested.document.license_family == "elastic-license"
    assert ingested.document.source_url == metadata.source_url
    assert ingested.document.commit_sha == "abc123"
    assert [chunk.anchor for chunk in ingested.chunks] == ["fix-search-results", "fix-search-results", "verify"]
    assert all(chunk.source_url.startswith("https://github.com/elastic/docs-content/blob/abc123/") for chunk in ingested.chunks)


def test_deterministic_chunk_ids_use_repo_path_anchor_and_index() -> None:
    expected = hashlib.sha256("elastic/docs-content:guide/page.md:intro:2".encode()).hexdigest()

    assert make_chunk_id("elastic/docs-content", "guide/page.md", "intro", 2) == expected


def test_classification_and_license_defaults_are_deterministic() -> None:
    assert classify_content_type("elastic/docs-content", "release-notes/8.14.md") == "release_note"
    assert classify_content_type("elastic/elasticsearch-labs", "example-apps/chatbot/README.md") == "example"
    assert classify_content_type("elastic/labs-releases", "indicators/ref7001/README.md") == "release_metadata"
    assert license_family_for_repo("unknown/repo") == "unknown"
