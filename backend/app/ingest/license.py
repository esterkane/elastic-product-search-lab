from __future__ import annotations


LICENSE_BY_REPO: dict[str, str] = {
    "elastic/docs-content": "elastic-license",
    "elastic/elasticsearch-labs": "apache-2.0",
    "elastic/labs-releases": "elastic-license",
}


def license_family_for_repo(repo: str) -> str:
    return LICENSE_BY_REPO.get(repo, "unknown")
