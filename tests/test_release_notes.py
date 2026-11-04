import hashlib
import subprocess
import sys

import pytest

from scripts.release_notes import render_release_notes

from .test_release import artifacts

METADATA = (
    "Requires-Python: >=3.13\n"
    "License-Expression: MIT\n"
    "Classifier: Programming Language :: Python :: 3 :: Only\n"
    "Classifier: Programming Language :: Python :: 3.13\n"
    "Classifier: Programming Language :: Python :: 3.14\n"
    "Classifier: Programming Language :: Python :: 3.15\n"
)


@pytest.mark.parametrize("version", ["1.2.3", "1.2.3a1", "1.2.3b2", "1.2.3rc1"])
def test_release_overview_uses_exact_artifacts(tmp_path, version):
    artifacts(tmp_path, version, version, METADATA)
    notes = render_release_notes("v" + version, "Peakora-VPN/telemt-sdk", tmp_path)
    assert f'uv add "telemt-sdk=={version}"' in notes
    assert f'python -m pip install --upgrade "telemt-sdk=={version}"' in notes
    assert f"https://pypi.org/project/telemt-sdk/{version}/" in notes
    assert f"/blob/v{version}/README.md" in notes
    assert "/blob/main/" not in notes
    assert "`3.13`, `3.14`, `3.15`" in notes
    assert "Python `>=3.13`" in notes
    assert "| Лицензия | [MIT]" in notes
    assert ("Предварительный выпуск" in notes) == (version != "1.2.3")
    assert ("Это предварительная версия" in notes) == (version != "1.2.3")
    for path in tmp_path.iterdir():
        assert f"/releases/download/v{version}/{path.name}" in notes
        assert f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}" in notes
        assert f"{path.stat().st_size:,} байт" in notes


def test_python_compatibility_is_not_hardcoded(tmp_path):
    artifacts(tmp_path, "2.0.0", "2.0.0", METADATA.replace("3.13", "3.16"))
    notes = render_release_notes("v2.0.0", "Example/sdk-fork", tmp_path)
    assert "`3.16`, `3.14`, `3.15`" in notes
    assert "Python `>=3.16`" in notes
    assert "3.13" not in notes
    assert "github.com/Example/sdk-fork" in notes
    assert "Peakora-VPN" not in notes


def test_incomplete_package_metadata_is_rejected(tmp_path):
    artifacts(tmp_path, "1.2.3", "1.2.3")
    with pytest.raises(ValueError, match="Python versions and a license"):
        render_release_notes("v1.2.3", "Peakora-VPN/telemt-sdk", tmp_path)


def test_tag_mismatch_is_rejected_before_rendering(tmp_path):
    artifacts(tmp_path, "1.2.3", "1.2.4", METADATA)
    with pytest.raises(ValueError, match="does not match"):
        render_release_notes("v1.2.3", "Peakora-VPN/telemt-sdk", tmp_path)


def test_invalid_repository_is_rejected(tmp_path):
    artifacts(tmp_path, "1.2.3", "1.2.3", METADATA)
    with pytest.raises(ValueError, match="owner/repository"):
        render_release_notes("v1.2.3", "invalid/repo?query", tmp_path)


def test_cli_writes_utf8_markdown(tmp_path):
    artifacts(tmp_path, "1.2.3", "1.2.3", METADATA)
    output = tmp_path / "notes.md"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.release_notes",
            "--tag",
            "v1.2.3",
            "--repository",
            "Peakora-VPN/telemt-sdk",
            "--dist",
            str(tmp_path),
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
    )
    assert "## 🚀 Установка и обновление" in output.read_text(encoding="utf-8")
