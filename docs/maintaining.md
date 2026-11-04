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
5. Creates a GitHub Release with generated notes and distribution attachments.

Prerelease tags are marked as prereleases on GitHub. A publish job can be retried;
`uv publish --check-url` checks existing distribution files. Do not move a released tag
or reuse a published version for different contents. Publish a new version instead.

CI and PyPI badges in the README reflect the external services. Their status becomes
available after the workflow has run and the first package release has been published.
