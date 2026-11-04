import io
import tarfile
from zipfile import ZipFile

import pytest

from scripts.check_release import check_release


def artifacts(directory, wheel_version, source_version):
    with ZipFile(directory / "package.whl", "w") as wheel:
        wheel.writestr(
            "telemt_sdk.dist-info/METADATA", f"Name: telemt-sdk\nVersion: {wheel_version}\n"
        )
    with tarfile.open(directory / "package.tar.gz", "w:gz") as source:
        content = f"Name: telemt-sdk\nVersion: {source_version}\n".encode()
        info = tarfile.TarInfo("telemt_sdk/PKG-INFO")
        info.size = len(content)
        source.addfile(info, io.BytesIO(content))


@pytest.mark.parametrize("version", ["1.2.3", "1.2.3rc1", "1.2.3a1", "1.2.3b1"])
def test_release_matches_artifacts(tmp_path, version):
    artifacts(tmp_path, version, version)
    check_release("v" + version, tmp_path)


@pytest.mark.parametrize("tag", ["1.2.3", "v1.2", "vlatest", "v1.2.3+dirty"])
def test_invalid_tag(tmp_path, tag):
    with pytest.raises(ValueError, match="Expected vX.Y.Z"):
        check_release(tag, tmp_path)


@pytest.mark.parametrize(
    ("wheel", "source"),
    [
        ("1.2.3.dev1", "1.2.3"),
        ("1.2.3", "1.2.4"),
        ("1.2.3+dirty", "1.2.3+dirty"),
    ],
)
def test_mismatched_artifact_version(tmp_path, wheel, source):
    artifacts(tmp_path, wheel, source)
    with pytest.raises(ValueError, match="does not match"):
        check_release("v1.2.3", tmp_path)


def test_missing_artifacts(tmp_path):
    with pytest.raises(ValueError, match="exactly one"):
        check_release("v1.2.3", tmp_path)
