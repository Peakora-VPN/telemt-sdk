import subprocess
import sys
from pathlib import Path

import pytest

from scripts.release_notes import render_release_notes, version_key


@pytest.fixture
def repo(tmp_path):
    def git(*args):
        return subprocess.check_output(
            ["git", *args], cwd=tmp_path, encoding="utf-8", stderr=subprocess.PIPE
        ).strip()

    git("init", "-b", "main")
    git("config", "user.name", "SDK test")
    git("config", "user.email", "test@example.invalid")
    git("config", "commit.gpgsign", "false")
    git("config", "tag.gpgsign", "false")

    def commit(message, filename="src/telemt/client.py"):
        path = tmp_path / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write("change\n")
        git("add", ".")
        git("commit", "-m", message)
        return git("rev-parse", "HEAD")

    return tmp_path, git, commit


def test_first_release_includes_sdk_changes_not_readme_or_ci(repo):
    root, git, commit = repo
    sha = commit("feat(client): Add asynchronous client")
    commit("feat: Add sponsor banner", "README.md")
    commit("fix: Update release workflow", ".github/workflows/release.yml")
    git("tag", "v1.0.0")
    notes = render_release_notes("v1.0.0", "Example/sdk", root)
    assert "Add asynchronous client" in notes
    assert f"/commit/{sha}" in notes
    assert "/commits/v1.0.0" in notes
    assert "sponsor" not in notes and "workflow" not in notes
    assert "feat(client)" not in notes


def test_stable_release_compares_to_previous_stable_not_rc(repo):
    root, git, commit = repo
    commit("feat: Old feature")
    git("tag", "v1.0.0")
    commit("feat: Add quotas")
    git("tag", "v1.1.0rc1")
    commit("fix: Correct quota reset")
    git("tag", "v1.1.0")
    notes = render_release_notes("v1.1.0", "Example/sdk", root)
    assert "Old feature" not in notes
    assert "Add quotas" in notes and "Correct quota reset" in notes
    assert "/compare/v1.0.0...v1.1.0" in notes


def test_prerelease_compares_to_previous_prerelease(repo):
    root, git, commit = repo
    for tag in ("v1.0.0", "v1.1.0a1", "v1.1.0b1", "v1.1.0rc1"):
        commit(f"fix: Change in {tag}")
        git("tag", tag)
    notes = render_release_notes("v1.1.0rc1", "Example/sdk", root)
    assert "Change in v1.1.0rc1" in notes
    assert "Change in v1.1.0b1" not in notes
    assert "/compare/v1.1.0b1...v1.1.0rc1" in notes


def test_unrelated_branch_tag_is_not_a_baseline(repo):
    root, git, commit = repo
    commit("feat: Base feature")
    git("tag", "v1.0.0")
    git("checkout", "-b", "other")
    commit("feat: Unrelated change")
    git("tag", "v1.5.0")
    git("checkout", "main")
    commit("fix: Current change")
    git("tag", "v2.0.0")
    notes = render_release_notes("v2.0.0", "Example/sdk", root)
    assert "/compare/v1.0.0...v2.0.0" in notes
    assert "Unrelated change" not in notes


@pytest.mark.parametrize(
    "message",
    [
        "refactor!: Remove legacy API",
        "refactor(client)!: Remove legacy API",
        "refactor: Remove legacy API\n\nBREAKING CHANGE: Old method removed",
        "Remove legacy API\n\nBREAKING-CHANGE: Old method removed",
    ],
)
def test_breaking_changes_take_priority_over_recent_fixes(repo, message):
    root, git, commit = repo
    commit(message)
    for i in range(6):
        commit(f"fix: Fix {i}")
    git("tag", "v1.0.0")
    notes = render_release_notes("v1.0.0", "Example/sdk", root)
    bullets = [line for line in notes.splitlines() if line.startswith("- ")]
    assert len(bullets) == 5
    assert "**Несовместимое изменение:** Remove legacy API" in bullets[0]
    assert "Ещё 2" in notes


def test_maintenance_is_excluded_and_duplicate_titles_are_collapsed(repo):
    root, git, commit = repo
    for message in (
        "chore: Reformat",
        "test: Add tests",
        "unstructured change",
        "fix: Correct retries",
        "fix: Correct retries",
        "perf: Reduce allocations",
    ):
        commit(message)
    git("tag", "v1.0.0")
    notes = render_release_notes("v1.0.0", "Example/sdk", root)
    assert notes.count("Correct retries") == 1
    assert "Reduce allocations" in notes
    assert "Reformat" not in notes and "Add tests" not in notes
    assert "unstructured" not in notes


def test_empty_range_has_only_comparison_link(repo):
    root, git, commit = repo
    commit("feat: Existing feature")
    git("tag", "v1.0.0")
    git("tag", "v1.0.1")
    assert render_release_notes("v1.0.1", "Example/sdk", root) == (
        "[Полный список изменений](https://github.com/Example/sdk/compare/v1.0.0...v1.0.1)\n"
    )


def test_invalid_tag_and_repository_are_rejected():
    with pytest.raises(ValueError, match="Expected vX.Y.Z"):
        render_release_notes("--all", "Example/sdk")
    with pytest.raises(ValueError, match="owner/repository"):
        render_release_notes("v1.0.0", "https://github.com/Example/sdk")


def test_version_order_is_numeric():
    tags = (
        "v1.9.0",
        "v1.10.0a1",
        "v1.10.0b1",
        "v1.10.0rc1",
        "v1.10.0rc2",
        "v1.10.0rc10",
        "v1.10.0",
    )
    assert sorted(tags, key=version_key) == list(tags)
    assert version_key("not-a-release") is None


def test_cli_reads_the_tag_not_unreleased_head_and_preserves_utf8(repo):
    root, git, commit = repo
    commit("feat: Добавлен клиент [API]")
    git("tag", "v1.0.0")
    commit("fix: Not released yet")
    output = root / "notes.md"
    script = Path(__file__).parents[1] / "scripts/release_notes.py"
    subprocess.run(
        [
            sys.executable,
            str(script),
            "--tag",
            "v1.0.0",
            "--repository",
            "Example/sdk",
            "--output",
            str(output),
        ],
        cwd=root,
        check=True,
        capture_output=True,
    )
    notes = output.read_text(encoding="utf-8")
    assert r"Добавлен клиент \[API\]" in notes
    assert "Not released yet" not in notes
