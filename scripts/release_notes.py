"""Generate concise release highlights from the tagged SDK commit history."""

import argparse
import re
import subprocess
from pathlib import Path

TAG = re.compile(r"v([0-9]+)\.([0-9]+)\.([0-9]+)(?:(a|b|rc)([0-9]+))?")
CONVENTIONAL = re.compile(r"([a-z]+)(?:\([^\n)]+\))?(!)?:\s+(.+)", re.IGNORECASE)
BREAKING = re.compile(r"^BREAKING[ -]CHANGE:\s*\S", re.MULTILINE)


def version_key(tag: str) -> tuple[int, int, int, int, int] | None:
    match = TAG.fullmatch(tag)
    if match is None:
        return None
    return (
        int(match[1]),
        int(match[2]),
        int(match[3]),
        {"a": 0, "b": 1, "rc": 2, None: 3}[match[4]],
        int(match[5] or 0),
    )


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=root, encoding="utf-8", errors="strict"
    ).strip()


def render_release_notes(tag: str, repository: str, root: Path = Path(".")) -> str:
    target = version_key(tag)
    if target is None:
        raise ValueError("Expected vX.Y.Z, optionally followed by aN, bN, or rcN")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Expected a GitHub owner/repository")
    ref = f"refs/tags/{tag}"
    git(root, "rev-parse", "--verify", f"{ref}^{{commit}}")
    candidates = [
        (version, name)
        for name in git(root, "tag", "--merged", ref).splitlines()
        if (version := version_key(name)) is not None
        and version < target
        and (target[3] != 3 or version[3] == 3)
    ]
    previous = max(candidates)[1] if candidates else None
    revision_range = f"refs/tags/{previous}..{ref}" if previous else ref
    records = git(
        root,
        "log",
        "--no-merges",
        "--topo-order",
        "--format=%H%x00%s%x00%b%x00",
        revision_range,
        "--",
        "src/telemt",
        "pyproject.toml",
        "uv.lock",
    ).split("\0")
    changes: list[tuple[bool, str, str]] = []
    for index in range(0, len(records) - 1, 3):
        sha, subject, body = records[index : index + 3]
        match = CONVENTIONAL.fullmatch(subject)
        breaking = bool(BREAKING.search(body) or (match and match[2]))
        if not breaking and (match is None or match[1].lower() not in {"feat", "fix", "perf"}):
            continue
        title = match[3] if match else subject
        changes.append((breaking, title, sha.strip()))

    base_url = f"https://github.com/{repository}"
    bullets = []
    seen = set()
    for breaking, title, sha in sorted(changes, key=lambda change: not change[0]):
        if title.casefold() in seen:
            continue
        seen.add(title.casefold())
        title = re.sub(r"([\\`*_{}\[\]<>])", r"\\\1", title)
        prefix = "**Несовместимое изменение:** " if breaking else ""
        bullets.append(f"- {prefix}{title} ([{sha[:7]}]({base_url}/commit/{sha}))")

    sections = []
    if bullets:
        sections.append("## Главное\n\n" + "\n".join(bullets[:5]))
        if len(bullets) > 5:
            sections.append(f"Ещё {len(bullets) - 5} — в полном списке изменений.")
    compare = f"compare/{previous}...{tag}" if previous else f"commits/{tag}"
    sections.append(f"[Полный список изменений]({base_url}/{compare})")
    return "\n\n".join(sections) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(render_release_notes(args.tag, args.repository), encoding="utf-8")


if __name__ == "__main__":
    main()
