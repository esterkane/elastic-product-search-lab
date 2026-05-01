from tools import repo_inventory


FIXTURES = __file__.rsplit("tests", maxsplit=1)[0] + "tests/fixtures"


def fixture_path(name: str):
    from pathlib import Path

    return Path(FIXTURES) / name


def test_discover_top_level_dirs_sorts_directory_names() -> None:
    assert repo_inventory.discover_top_level_dirs(fixture_path("discovery")) == ["alpha", "nested", "zeta"]


def test_discover_key_config_files_is_top_level_and_sorted() -> None:
    assert repo_inventory.discover_key_config_files(fixture_path("discovery")) == ["package.json", "pyproject.toml"]


def test_license_detection_prefers_exact_license() -> None:
    repo_dir = fixture_path("licenses-exact")

    assert repo_inventory.discover_license_files(repo_dir) == ["LICENSE", "LICENSE.md", "NOTICE.txt"]
    assert repo_inventory.first_license_file(repo_dir) == "LICENSE"


def test_license_detection_falls_back_deterministically() -> None:
    assert repo_inventory.first_license_file(fixture_path("licenses-fallback")) == "COPYING"


def test_discover_project_files_and_workflows() -> None:
    repo_dir = fixture_path("project-files")

    assert repo_inventory.discover_named_files(repo_dir, repo_inventory.README_NAMES) == [
        "README.md",
        "docs/README.md",
    ]
    assert repo_inventory.discover_named_files(repo_dir, repo_inventory.CODEOWNERS_NAMES) == [".github/CODEOWNERS"]
    assert repo_inventory.discover_workflows(repo_dir) == [".github/workflows/ci.yml"]
