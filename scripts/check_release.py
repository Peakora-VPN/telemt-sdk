"""Fail before publishing if artifacts do not match an exact supported Git tag."""

import os
import re
import tarfile
from email.parser import BytesParser
from pathlib import Path
from zipfile import ZipFile


def check_release(tag: str, directory: Path) -> None:
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?", tag):
        raise ValueError("Expected vX.Y.Z, optionally followed by aN, bN, or rcN")
    wheels = list(directory.glob("*.whl"))
    sources = list(directory.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sources) != 1:
        raise ValueError("Expected exactly one wheel and one source distribution")
    with ZipFile(wheels[0]) as wheel:
        metadata_path = next(
            name for name in wheel.namelist() if name.endswith(".dist-info/METADATA")
        )
        wheel_metadata = wheel.read(metadata_path)
    with tarfile.open(sources[0]) as source:
        metadata_path = next(
            name
            for name in source.getnames()
            if name.count("/") == 1 and name.endswith("/PKG-INFO")
        )
        stream = source.extractfile(metadata_path)
        if stream is None:
            raise ValueError("Source metadata is missing")
        source_metadata = stream.read()
    for raw in (wheel_metadata, source_metadata):
        metadata = BytesParser().parsebytes(raw)
        if metadata["Name"] != "telemt-sdk" or metadata["Version"] != tag[1:]:
            raise ValueError("Distribution name/version does not match the release tag")


if __name__ == "__main__":
    check_release(os.environ["RELEASE_TAG"], Path("dist"))
