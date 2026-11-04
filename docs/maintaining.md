# Maintaining and publishing

This document is for repository maintainers. End-user installation and usage belong in
the [README](../README.md).

## One-time Trusted Publisher setup

Create a GitHub Actions environment named `pypi` in the repository settings. Configure
environment protection rules and allowed release tags according to your team's policy.
The publishing job in `.github/workflows/release.yml` references that environment.

On PyPI, add a Trusted Publisher. Use a pending publisher if `telemt-sdk` does not yet
exist, or add the publisher in the existing project's settings:

| PyPI field | Value |
| --- | --- |
| Project name | `telemt-sdk` |
| Owner | `Peakora-VPN` |
| Repository name | `telemt-sdk` |
| Workflow filename | `release.yml` |
| Environment name | `pypi` |

The repository field takes only the repository name, not its URL or `owner/repository`.
Use ordinary ASCII hyphens and no leading/trailing spaces. The workflow filename is
`release.yml`, not its display name and not `.github/workflows/release.yml`.
All values must match the actual GitHub repository and environment, including for forks.

Publishing uses GitHub OIDC and `id-token: write`; no PyPI API token secret is needed.
A pending publisher does not reserve a package name. See the official
[PyPI pending publisher guide](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
and [uv publishing guide](https://docs.astral.sh/uv/guides/integration/github/#publishing-to-pypi).

## Tag-based versions

`hatch-vcs` derives the package version from Git tags. There is no manually maintained
version constant: `telemt.__version__` reads installed package metadata.
Between tags, builds have a development version. Builds from a Git checkout need history
and tags; the published source distribution can be rebuilt without `.git`.

Accepted release tags are `vX.Y.Z`, `vX.Y.ZaN`, `vX.Y.ZbN` and `vX.Y.ZrcN`.
For example, after committing and reviewing the intended release:

```bash
git tag -a v0.1.0 -m "Release 0.1.0"
git push origin v0.1.0
```

Pushing the tag triggers `.github/workflows/release.yml`. It:

1. Runs the reusable CI workflow on that exact commit.
2. Downloads the wheel and source archive produced by CI.
3. Verifies the tag and both distribution metadata versions match.
4. Publishes those artifacts to PyPI using Trusted Publishing.
5. Creates a GitHub Release with changes for that release and distribution attachments.

Prerelease tags are marked as prereleases on GitHub. A publish job can be retried;
`uv publish --check-url` checks existing distribution files. Do not move a released tag
or reuse a published version for different contents. Publish a new version instead.

CI and PyPI badges in the README reflect the external services. Their status becomes
available after the workflow has run and the first package release has been published.

## Automatic release highlights

The workflow generates the release body from Git using `scripts/release_notes.py`.
No release-specific Markdown file, manually written summary or external service is needed.
The description contains up to five significant changes and a link to the full comparison.
Installation instructions, package metadata tables and the general SDK description stay in
README. Distribution files remain attached as release assets.

The generator reads the tagged commit, not the current checkout's uncommitted changes:

- A stable release compares with the highest earlier stable version reachable from its tag.
  This includes changes introduced during that release's alpha, beta and RC cycle.
- A prerelease compares with the highest earlier reachable version, including prereleases.
- The first release uses all history up to its tag.
- Only commits touching `src/telemt`, `pyproject.toml` or `uv.lock` are considered.
- `feat`, `fix` and `perf` commit subjects supply the highlights. `!` or a
  `BREAKING CHANGE:` / `BREAKING-CHANGE:` footer includes a breaking change of any type.
- Breaking changes come first, followed by the most recent relevant commits. Duplicate
  titles and merge commits are omitted. Additional changes remain in the comparison link.

Use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) for meaningful
SDK changes, for example `fix(users): preserve null when clearing a quota`.
The commit title's language and wording are preserved; the generator does not invent or
translate a description. Unstructured commits and maintenance-only changes are available
through the full comparison rather than presented as highlights. If no relevant changes
are found, the release body contains only that link.

Preview the exact automatically generated text for an existing tag:

```bash
uv run --no-project python -m scripts.release_notes \
  --tag v1.0.0 --repository Peakora-VPN/telemt-sdk \
  --output release-notes.md
```

This command reads local Git history and writes Markdown; it does not publish anything.
Full history and tags are required (`fetch-depth: 0` in CI). Release checks still verify
artifact versions before publishing. Existing releases are not overwritten on workflow
reruns. Prereleases retain GitHub's prerelease marker and are not marked Latest.
