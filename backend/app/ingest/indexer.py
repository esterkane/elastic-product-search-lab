from __future__ import annotations

import asyncio
import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.app.embeddings.client import EmbeddingClient
from backend.app.ingest.chunker import IngestedDocument, SourceMetadata, build_source_url, ingest_markdown
from backend.app.vector.qdrant_client import QdrantVectorRepository, VectorPoint, vector_payload


@dataclass(frozen=True)
class RepoSpec:
    slug: str
    url: str
    directory: str
    default_branch: str = "main"


@dataclass
class IndexingResult:
    status: str
    repo_url: str
    branch: str | None
    message: str
    repos_scanned: int = 0
    documents_scanned: int = 0
    chunks_indexed: int = 0
    new_chunks: int = 0
    updated_chunks: int = 0
    unchanged_chunks: int = 0
    errors: list[str] = field(default_factory=list)


REPOSITORIES: tuple[RepoSpec, ...] = (
    RepoSpec("elastic/docs-content", "https://github.com/elastic/docs-content.git", "docs-content"),
    RepoSpec("elastic/docs-builder", "https://github.com/elastic/docs-builder.git", "docs-builder"),
    RepoSpec("elastic/docs", "https://github.com/elastic/docs.git", "docs"),
    RepoSpec("elastic/elasticsearch-labs", "https://github.com/elastic/elasticsearch-labs.git", "elasticsearch-labs"),
    RepoSpec("elastic/labs-releases", "https://github.com/elastic/labs-releases.git", "labs-releases"),
)


class RepositoryIndexer:
    def __init__(
        self,
        *,
        sources_dir: Path,
        engine: AsyncEngine,
        embedding_client: EmbeddingClient,
        vector_repository: QdrantVectorRepository,
        embedding_batch_size: int = 8,
    ) -> None:
        self.sources_dir = sources_dir
        self.engine = engine
        self.embedding_client = embedding_client
        self.vector_repository = vector_repository
        self.embedding_batch_size = embedding_batch_size

    async def index(
        self,
        *,
        repo_url: str | None = None,
        repo_slug: str | None = None,
        branch: str | None = None,
        force: bool = False,
        update_sources: bool = True,
        max_files: int | None = None,
    ) -> IndexingResult:
        specs = resolve_repositories(repo_url=repo_url, repo_slug=repo_slug)
        display_repo = repo_url or repo_slug or "all"
        result = IndexingResult(status="completed", repo_url=display_repo, branch=branch, message="")

        await self.ensure_schema()
        self.sources_dir.mkdir(parents=True, exist_ok=True)

        for spec in specs:
            repo_path = self.sources_dir / spec.directory
            try:
                if update_sources:
                    await asyncio.to_thread(sync_repository, spec, repo_path, branch)
                commit_sha = await asyncio.to_thread(read_git_value, repo_path, ["rev-parse", "HEAD"], "unknown")
                active_branch = branch or await asyncio.to_thread(
                    read_git_value,
                    repo_path,
                    ["branch", "--show-current"],
                    spec.default_branch,
                )
                indexed = await self.index_local_repo(
                    spec=spec,
                    repo_path=repo_path,
                    commit_sha=commit_sha,
                    branch=active_branch,
                    force=force,
                    max_files=max_files,
                )
            except Exception as exc:  # pragma: no cover - defensive reporting for live indexing
                result.errors.append(f"{spec.slug}: {exc}")
                continue

            result.repos_scanned += 1
            result.documents_scanned += indexed.documents_scanned
            result.chunks_indexed += indexed.chunks_indexed
            result.new_chunks += indexed.new_chunks
            result.updated_chunks += indexed.updated_chunks
            result.unchanged_chunks += indexed.unchanged_chunks

        if result.errors and result.repos_scanned == 0:
            result.status = "failed"
            result.message = "No repositories were indexed."
        elif result.errors:
            result.status = "partial"
            result.message = "Indexed available repositories; some repositories reported errors."
        else:
            result.message = "Index is up to date."
        return result

    async def index_local_repo(
        self,
        *,
        spec: RepoSpec,
        repo_path: Path,
        commit_sha: str,
        branch: str | None,
        force: bool,
        max_files: int | None,
    ) -> IndexingResult:
        if not repo_path.exists():
            raise FileNotFoundError(f"{repo_path} does not exist")

        documents = [
            document
            for document in iter_markdown_files(repo_path)
            if ".git" not in document.parts
        ]
        if max_files is not None:
            documents = documents[:max_files]

        existing = await self.load_existing_content(spec.slug)
        pending_points: list[VectorPoint] = []
        rows: list[dict[str, object]] = []
        result = IndexingResult(status="completed", repo_url=spec.url, branch=branch, message="")

        for document_path in documents:
            relative_path = document_path.relative_to(repo_path).as_posix()
            markdown = await asyncio.to_thread(document_path.read_text, encoding="utf-8", errors="replace")
            metadata = SourceMetadata(
                repo=spec.slug,
                repo_url=spec.url,
                path=relative_path,
                source_url=build_source_url(spec.url, commit_sha, relative_path),
                commit_sha=commit_sha,
                default_branch=branch,
            )
            ingested = ingest_markdown(markdown, metadata)
            result.documents_scanned += 1
            rows.extend(chunk_rows(ingested))
            chunk_content = {chunk.chunk_id: chunk.content for chunk in ingested.chunks}

            for point in points_for_ingested_document(ingested):
                previous_content = existing.get(point.id)
                if previous_content is None:
                    result.new_chunks += 1
                elif previous_content != chunk_content[point.id]:
                    result.updated_chunks += 1
                elif force:
                    result.updated_chunks += 1
                else:
                    result.unchanged_chunks += 1
                    continue
                pending_points.append(point)

        if pending_points:
            await self.embed_and_attach_vectors(pending_points)
            await self.upsert_vectors(pending_points)
        if rows:
            await self.upsert_chunks(rows)
        result.chunks_indexed = len(pending_points)
        return result

    async def embed_and_attach_vectors(self, points: list[VectorPoint]) -> None:
        for start in range(0, len(points), self.embedding_batch_size):
            batch = points[start : start + self.embedding_batch_size]
            vectors = await self.embedding_client.embed([str(point.payload.get("text") or "") for point in batch])
            for point, vector in zip(batch, vectors, strict=True):
                point.vector[:] = vector

    async def upsert_vectors(self, points: list[VectorPoint]) -> None:
        if not points:
            return
        await self.vector_repository.ensure_collection(len(points[0].vector))
        await self.vector_repository.upsert(points)

    async def ensure_schema(self) -> None:
        async with self.engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS document_chunks (
                        id TEXT PRIMARY KEY,
                        content TEXT NOT NULL,
                        metadata JSONB NOT NULL,
                        source_url TEXT NOT NULL,
                        search_vector TSVECTOR NOT NULL,
                        commit_sha TEXT NOT NULL,
                        repo TEXT NOT NULL,
                        path TEXT NOT NULL,
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
                )
            )
            await connection.execute(
                text("CREATE INDEX IF NOT EXISTS document_chunks_search_idx ON document_chunks USING GIN (search_vector)")
            )
            await connection.execute(
                text("CREATE INDEX IF NOT EXISTS document_chunks_metadata_idx ON document_chunks USING GIN (metadata)")
            )

    async def load_existing_content(self, repo: str) -> dict[str, str]:
        async with self.engine.connect() as connection:
            result = await connection.execute(
                text("SELECT id, content FROM document_chunks WHERE repo = :repo"),
                {"repo": repo},
            )
        return {str(row.id): str(row.content) for row in result}

    async def upsert_chunks(self, rows: list[dict[str, object]]) -> None:
        statement = text(
            """
            INSERT INTO document_chunks (
                id, content, metadata, source_url, search_vector, commit_sha, repo, path, updated_at
            )
            VALUES (
                :id,
                :content,
                CAST(:metadata AS jsonb),
                :source_url,
                to_tsvector('english', :content),
                :commit_sha,
                :repo,
                :path,
                now()
            )
            ON CONFLICT (id) DO UPDATE SET
                content = EXCLUDED.content,
                metadata = EXCLUDED.metadata,
                source_url = EXCLUDED.source_url,
                search_vector = EXCLUDED.search_vector,
                commit_sha = EXCLUDED.commit_sha,
                repo = EXCLUDED.repo,
                path = EXCLUDED.path,
                updated_at = now()
            """
        )
        async with self.engine.begin() as connection:
            await connection.execute(statement, rows)


def points_for_ingested_document(ingested: IngestedDocument) -> list[VectorPoint]:
    title = ingested.document.title
    points: list[VectorPoint] = []
    for chunk in ingested.chunks:
        heading_path = " > ".join(part for part in [title, chunk.heading] if part)
        payload = vector_payload(
            repo=chunk.repo,
            path=chunk.path,
            title=title,
            heading_path=heading_path or None,
            content_type=chunk.content_type,
            license_family=chunk.license_family,
            source_url=chunk.source_url,
        )
        payload["commit_sha"] = chunk.commit_sha
        payload["text"] = chunk.content
        points.append(VectorPoint(id=chunk.chunk_id, vector=[], payload=payload, source_url=chunk.source_url))
    return points


def chunk_rows(ingested: IngestedDocument) -> list[dict[str, object]]:
    title = ingested.document.title
    rows: list[dict[str, object]] = []
    for chunk in ingested.chunks:
        heading_path = " > ".join(part for part in [title, chunk.heading] if part)
        metadata = vector_payload(
            repo=chunk.repo,
            path=chunk.path,
            title=title,
            heading_path=heading_path or None,
            content_type=chunk.content_type,
            license_family=chunk.license_family,
            source_url=chunk.source_url,
        )
        metadata["commit_sha"] = chunk.commit_sha
        metadata["anchor"] = chunk.anchor
        metadata["chunk_index"] = chunk.chunk_index
        rows.append(
            {
                "id": chunk.chunk_id,
                "content": chunk.content,
                "metadata": json.dumps(metadata, sort_keys=True),
                "source_url": chunk.source_url,
                "commit_sha": chunk.commit_sha,
                "repo": chunk.repo,
                "path": chunk.path,
            }
        )
    return rows


def iter_markdown_files(repo_path: Path) -> list[Path]:
    return sorted(
        [path for pattern in ("*.md", "*.mdx") for path in repo_path.rglob(pattern)],
        key=lambda path: path.relative_to(repo_path).as_posix().lower(),
    )


def resolve_repositories(repo_url: str | None, repo_slug: str | None) -> list[RepoSpec]:
    if not repo_url and not repo_slug:
        return list(REPOSITORIES)
    if repo_url in {"all", "*"}:
        return list(REPOSITORIES)

    normalized_url = (repo_url or "").removesuffix(".git").rstrip("/")
    for spec in REPOSITORIES:
        if repo_slug == spec.slug or normalized_url == spec.url.removesuffix(".git"):
            return [spec]
    raise ValueError(f"Unknown repository: {repo_slug or repo_url}")


def sync_repository(spec: RepoSpec, repo_path: Path, branch: str | None) -> None:
    repo_path.parent.mkdir(parents=True, exist_ok=True)
    if not repo_path.exists():
        command = ["git", "clone", "--depth", "1"]
        if branch:
            command.extend(["--branch", branch])
        command.extend([spec.url, str(repo_path)])
        run_git(command, repo_path.parent)
        return

    run_git(["git", "-C", str(repo_path), "fetch", "--prune"], repo_path)
    if branch:
        run_git(["git", "-C", str(repo_path), "checkout", branch], repo_path)
    run_git(["git", "-C", str(repo_path), "pull", "--ff-only"], repo_path)


def read_git_value(repo_path: Path, args: list[str], fallback: str) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_path), *args],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return fallback
    return completed.stdout.strip() or fallback


def run_git(command: list[str], cwd: Path) -> None:
    completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=300)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "git command failed"
        raise RuntimeError(detail)
