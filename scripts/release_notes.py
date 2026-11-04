"""Render release information from the exact distributions being published."""

import argparse
import hashlib
import re
from email.parser import BytesParser
from pathlib import Path
from urllib.parse import quote
from zipfile import ZipFile

from scripts.check_release import check_release


def render_release_notes(tag: str, repository: str, directory: Path) -> str:
    check_release(tag, directory)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Expected a GitHub owner/repository")
    with ZipFile(next(directory.glob("*.whl"))) as wheel:
        metadata_path = next(n for n in wheel.namelist() if n.endswith(".dist-info/METADATA"))
        metadata = BytesParser().parsebytes(wheel.read(metadata_path))
    python_versions = [
        classifier.rsplit(" :: ", 1)[1]
        for classifier in metadata.get_all("Classifier", [])
        if re.fullmatch(r"Programming Language :: Python :: 3\.\d+", classifier)
    ]
    requires_python = metadata["Requires-Python"]
    license_expression = metadata["License-Expression"]
    if not python_versions or not requires_python or not license_expression:
        raise ValueError("Release metadata must include Python versions and a license")

    version = tag[1:]
    base_url = f"https://github.com/{repository}"
    source_url = f"{base_url}/blob/{tag}"
    pypi_url = f"https://pypi.org/project/telemt-sdk/{version}/"
    python_label = quote(" | ".join(python_versions), safe="")
    prerelease = bool(re.search(r"(?:a|b|rc)\d+$", version))
    release_kind = "Предварительный выпуск" if prerelease else "Обычный выпуск"
    notice = (
        "> 🧪 Это предварительная версия для тестирования. "
        "Установка ниже явно выбирает этот выпуск.\n\n"
        if prerelease
        else ""
    )
    assets = sorted([*directory.glob("*.whl"), *directory.glob("*.tar.gz")])
    rows = []
    checksums = []
    for asset in assets:
        kind = "Wheel — установка" if asset.suffix == ".whl" else "Исходный код — sdist"
        url = f"{base_url}/releases/download/{tag}/{quote(asset.name)}"
        rows.append(f"| [{asset.name}]({url}) | {kind} | {asset.stat().st_size:,} байт |")
        checksums.append(f"{hashlib.sha256(asset.read_bytes()).hexdigest()}  {asset.name}")
    asset_table = "\n".join(rows)
    checksum_text = "\n".join(checksums)

    return f"""[![PyPI](https://img.shields.io/badge/PyPI-{version}-3776AB?style=flat-square&logo=pypi&logoColor=white)]({pypi_url})
[![Python](https://img.shields.io/badge/Python-{python_label}-3776AB?style=flat-square&logo=python&logoColor=white)]({source_url}/README.md#совместимость)
[![License](https://img.shields.io/badge/License-{quote(license_expression)}-22C55E?style=flat-square)]({source_url}/LICENSE)

Асинхронный типизированный Python SDK для [Telemt](https://github.com/telemt/telemt):
управление пользователями, квотами, конфигурацией и WEB-сессиями через Control API.

{notice}## 📌 О выпуске

| | |
| --- | --- |
| Версия | **{version}** · {release_kind} |
| Поддерживаемый Python | {", ".join(f"`{v}`" for v in python_versions)} |
| Требование пакета | Python `{requires_python}` |
| Лицензия | [{license_expression}]({source_url}/LICENSE) |
| Исходный код | [Тег `{tag}`]({base_url}/tree/{tag}) |

## 🚀 Установка и обновление

**uv**

```bash
uv add "telemt-sdk=={version}"
```

**pip**

```bash
python -m pip install --upgrade "telemt-sdk=={version}"
```

Импорт в Python: `from telemt import TelemtClient`.
Команды устанавливают именно этот выпуск, включая предварительные версии.

## 📖 Документация

[Быстрый старт]({source_url}/README.md#быстрый-старт) ·
[English README]({source_url}/README.en.md) ·
[Справочник API]({source_url}/docs/api-reference.md) ·
[Сообщить об ошибке]({base_url}/issues)

## 📦 Файлы выпуска

| Файл | Назначение | Размер |
| --- | --- | --- |
{asset_table}

<details>
<summary>🔐 Контрольные суммы SHA-256</summary>

```text
{checksum_text}
```

</details>

---

"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(
        render_release_notes(args.tag, args.repository, args.dist), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
