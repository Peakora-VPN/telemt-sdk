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
5. Creates a GitHub Release with a Russian overview, categorized changes and distribution attachments.

Prerelease tags are marked as prereleases on GitHub. A publish job can be retried;
`uv publish --check-url` checks existing distribution files. Do not move a released tag
or reuse a published version for different contents. Publish a new version instead.

CI and PyPI badges in the README reflect the external services. Their status becomes
available after the workflow has run and the first package release has been published.

## Release presentation

Every new release has the title `telemt-sdk vX.Y.Z` and an overview containing:

- Clickable PyPI, Python and license badges tied to that release.
- The exact version, supported Python versions, package requirement and license.
- Copyable uv and pip installation/update commands pinned to the published version.
- Russian/English documentation and API reference links pointing to the release tag.
- Download links, sizes and SHA-256 checksums for the wheel and source distribution.
- A clear notice for alpha, beta and release-candidate builds; these are not marked Latest.

`scripts/release_notes.py` reads compatibility and license information from the verified
wheel metadata, and hashes the actual distribution files. The workflow prepares this
overview before publishing and passes it through `--notes-file`. GitHub appends generated
release notes with pull requests, contributors and the full changelog link.

Use these PR labels to organize the generated changes. The first matching category wins:

| Label | Release section |
| --- | --- |
| `breaking-change` | Changes affecting compatibility |
| `enhancement`, `feature` | New features |
| `bug`, `fix` | Fixes |
| `documentation` | Documentation |
| `dependencies` | Dependencies |
| `tests`, `ci` | Tests and automation |
| Other / no label | Other changes |
| `skip-changelog` | Excluded from generated notes |

Category titles are configured in `.github/release.yml` (separate from the publishing
workflow in `.github/workflows/release.yml`). Write PR titles as useful descriptions for
SDK users; explain any migration in the PR linked from the compatibility section.
GitHub categorizes merged PRs; changes committed directly remain accessible through the
full changelog. No labels are required for a PR to appear in the catch-all category.

To preview the overview locally using distributions built from the matching release tag:

```bash
uv build
uv run --no-project python -m scripts.release_notes \
  --tag v0.1.0 --repository Peakora-VPN/telemt-sdk \
  --output dist/release-notes.md
```

The renderer requires exactly one wheel and one source archive with the matching version.
The local preview does not call GitHub or publish anything; GitHub's generated changelog
is appended when the release is created. Existing releases are left unchanged on workflow
reruns, preserving any manual edits made after publication.
