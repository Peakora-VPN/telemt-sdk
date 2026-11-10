<p align="center">
  <a href="https://github.com/Peakora-VPN/telemt-sdk/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/Peakora-VPN/telemt-sdk/ci.yml?style=for-the-badge&amp;logo=githubactions&amp;logoColor=white&amp;label=CI" alt="CI status"></a>
  <a href="https://pypi.org/project/telemt-sdk/"><img src="https://img.shields.io/pypi/v/telemt-sdk?style=for-the-badge&amp;logo=pypi&amp;logoColor=white&amp;color=3776AB" alt="PyPI version"></a>
  <a href="#совместимость"><img src="https://img.shields.io/badge/Python-3.13%20%7C%203.14%20%7C%203.15-3776AB?style=for-the-badge&amp;logo=python&amp;logoColor=white" alt="Python 3.13, 3.14 and 3.15"></a>
  <a href="https://github.com/Peakora-VPN/telemt-sdk/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge" alt="MIT license"></a>
</p>
<p align="center">
  <a href="https://docs.astral.sh/uv/"><img src="https://img.shields.io/badge/managed%20with-uv-DE5FE9?style=flat-square&amp;logo=uv" alt="Managed with uv"></a>
  <a href="https://docs.astral.sh/ruff/"><img src="https://img.shields.io/badge/code%20style-Ruff-D7FF64?style=flat-square&amp;logo=ruff&amp;logoColor=black" alt="Code style: Ruff"></a>
  <a href="https://typing.python.org/"><img src="https://img.shields.io/badge/typing-PEP%20561-6366F1?style=flat-square" alt="Typed Python package"></a>
</p>

<p align="center"><a href="https://github.com/Peakora-VPN/telemt-sdk/blob/main/README.md">Русский</a> · <a href="https://github.com/Peakora-VPN/telemt-sdk/blob/main/README.en.md">English</a></p>

<h1 align="center">telemt-sdk</h1>
<p align="center">Асинхронный типизированный Python SDK для Telemt Control API.</p>
<p align="center">
  <a href="#быстрый-старт">Быстрый старт</a> ·
  <a href="https://github.com/Peakora-VPN/telemt-sdk/blob/main/docs/api-reference.md">Справочник API</a> ·
  <a href="https://github.com/Peakora-VPN/telemt-sdk/blob/main/CONTRIBUTING.md">Участие в разработке</a> ·
  <a href="https://github.com/Peakora-VPN/telemt-sdk/issues">Сообщить об ошибке</a>
</p>

Управляйте пользователями прокси, квотами, конфигурацией, диагностикой и WEB-сессиями из Python.
`TelemtClient` объединяет операции в ресурсные объекты, переиспользует HTTP-соединения
и возвращает Pydantic-модели с конкретными аннотациями типов, включая вложенные данные.

- **54 операции API:** пользователи, состояние сервиса, статистика, конфигурация, политика доступа, обнаружение возможностей и управление WEB runtime.
- **Полностью асинхронный интерфейс:** `async with`, `await` и параллельное чтение через `asyncio.gather`.
- **Типизированные запросы и ответы:** валидация входных данных, подсказки IDE и маркер `py.typed`.
- **Контроль конкурентных изменений:** передача ревизии ответа (`revision=`) и токена runtime (`runtime_match=`) для защиты обновлений конфигурации и политики доступа.
- **Понятные ошибки:** отдельные классы исключений сохраняют HTTP-статус, код Telemt, идентификатор запроса и структурированные детали ошибки (`path`, `code`, `message`).

SDK работает с HTTP API управления [Telemt](https://github.com/telemt/telemt).
Передачу MTProto-трафика и подключения клиентов Telegram обеспечивает сам Telemt.

## Установка

Требуется Python **3.13, 3.14 или 3.15**. Имя пакета — `telemt-sdk`, имя импорта — `telemt`.

Установка из [PyPI](https://pypi.org/project/telemt-sdk/):

```bash
uv add telemt-sdk
```

Или через pip:

```bash
python -m pip install telemt-sdk
```

Настройка окружения для разработки описана в [CONTRIBUTING.md](CONTRIBUTING.md).

## Быстрый старт

Включите Control API в конфигурации Telemt и задайте `TELEMT_AUTH_HEADER` равным точному
значению `server.api.auth_header`:

```python
import asyncio
import os

from telemt import TelemtClient


async def main() -> None:
    async with TelemtClient(
        "http://127.0.0.1:9091",
        auth_header=os.environ["TELEMT_AUTH_HEADER"],
    ) as client:
        health = await client.health.get()
        print(health.data.status)

        users = await client.users.list()
        for user in users.data:
            print(user.username, user.enabled, user.current_connections)


asyncio.run(main())
```

SDK передаёт `auth_header` в заголовке `Authorization` без изменений и не добавляет `Bearer`.
Если на сервере настроено значение `Bearer ...`, передавайте строку целиком.
Если авторизация не настроена, аргумент можно опустить. Используйте адрес слушателя
Control API, а не порт MTProto или WEB ingress.

Следующие примеры выполняются внутри `async with TelemtClient(...) as client`
в асинхронной функции, как в быстром старте.

## Настройка клиента

| Аргумент | По умолчанию | Назначение |
| --- | --- | --- |
| `base_url` | Обязателен | Абсолютный HTTP(S) URL. `/v1` добавляется, если отсутствует. Префикс reverse proxy сохраняется. |
| `auth_header` | `None` | Точное значение заголовка `Authorization`, настроенного на сервере. |
| `timeout` | `30.0` | Тайм-аут HTTPX в секундах или `httpx.Timeout` с отдельными лимитами подключения, чтения, записи и ожидания соединения. |
| `http_client` | `None` | Необязательный `httpx.AsyncClient` для настройки TLS, прокси, транспорта и пула соединений. |

Адреса `https://proxy.example.com/control` и `https://proxy.example.com/control/v1`
оба направляют запросы в `/control/v1/...`. Учётные данные, query-параметры и фрагменты
в `base_url` не допускаются.

Используйте один клиент для нескольких запросов в пределах одного event loop:

```python
health, stats = await asyncio.gather(client.health.get(), client.stats.summary())
print(stats.data.connections_total)
```

Закрывайте соединения через `async with` или `await client.aclose()`. Закрытый клиент
нельзя использовать повторно. Если вы передаёте собственный HTTPX-клиент, его временем
жизни управляете вы:

```python
import httpx

async with httpx.AsyncClient(limits=httpx.Limits(max_connections=20)) as http:
    async with TelemtClient(
        "https://proxy.example.com",
        auth_header=os.environ["TELEMT_AUTH_HEADER"],
        timeout=httpx.Timeout(30.0, connect=5.0),
        http_client=http,
    ) as client:
        info = await client.system.info()
```

Параметры SDK и явно переданная авторизация имеют приоритет над настройками HTTPX.
Редиректы и автоматические повторы запросов отключены: изменение могло дойти до сервера
до истечения тайм-аута.

### Хуки HTTP

Передайте объекты `ClientHook` через `hooks`, переопределив нужные методы:

```python
import httpx
from telemt import ClientHook, TelemtClient


class LoggingHook(ClientHook):
    async def on_request(self, request: httpx.Request) -> None:
        print(request.method, request.url.path)

    async def on_response(self, response: httpx.Response) -> None:
        print(response.status_code)


async with TelemtClient(
    "http://127.0.0.1:9091",
    auth_header=os.environ["TELEMT_AUTH_HEADER"],
    hooks=[LoggingHook()],
) as client:
    await client.health.get()
```

## Пользователи и квоты

```python
from telemt.models import CreateUserRequest, PatchUserRequest, RotateSecretRequest

created = await client.users.create(
    CreateUserRequest(
        username="alice",
        max_tcp_conns=10,
        data_quota_bytes=10_000_000_000,
        quota_period="monthly",
    )
)
# created.data.secret содержит сгенерированный секрет; не записывайте его в логи.
print(created.data.user.username)

updated = await client.users.update(
    "alice",
    PatchUserRequest(max_tcp_conns=20, expiration_rfc3339="2027-01-01T00:00:00Z"),
    revision=created.revision,
)

rotated = await client.users.rotate_secret("alice", RotateSecretRequest())
await client.users.reset_quota("alice")
await client.users.disable("alice")
await client.users.enable("alice")
# Удаляйте пользователя явно, когда учётная запись больше не нужна:
# await client.users.delete("alice")
```

Секреты и рекламные теги состоят из 32 шестнадцатеричных символов. Имя пользователя
содержит от 1 до 64 латинских букв, цифр, точек, дефисов или подчёркиваний. Имена `.`
и `..` отклоняются, поскольку HTTPX нормализует такие сегменты пути. Для периодического
сброса квоты доступны `daily`, `weekly` и `monthly`; при создании пользователя требуется
положительное значение `data_quota_bytes`.

Поле `source_deny` принимает список CIDR-префиксов IPv4 или IPv6 (`"203.0.113.0/24"`).
Список запрещает пользователю исходящие подключения из указанных сетей; после изменения
политики списков требуется перезагрузка поколения runtime, о чём сообщает
`UserInfo.source_deny_status.runtime_reload_required`. При создании явно переданный
`source_deny=None` сериализуется как JSON `null`, а пропущенное поле не отправляется вовсе.

### Семантика PATCH

Пропущенное поле, `None` и ноль имеют разное значение:

| Запрос | Результат |
| --- | --- |
| `PatchUserRequest()` | Оставить настройки без изменений. |
| `PatchUserRequest(max_tcp_conns=None)` | Удалить индивидуальное ограничение пользователя. |
| `PatchUserRequest(max_tcp_conns=0)` | Передать явный ноль; его смысл для этой настройки определяет Telemt. |
| `PatchUserRequest(enabled=False)` | Отключить пользователя. |
| `PatchUserRequest(secret=None)` | Оставить секрет без изменений, как это делает Telemt. |
| `PatchUserRequest(source_deny=["203.0.113.0/24"])` | Заменить список запрещённых сетей. |
| `PatchUserRequest(source_deny=None)` | Очистить список запрещённых сетей. |

Для генерации нового секрета используйте `rotate_secret()`. Модели запросов отклоняют
неизвестные поля и недопустимые значения. Проверки, зависящие от состояния сервера,
например существование пользователя, выполняет Telemt и возвращает соответствующую ошибку API.

### Проверка расхода квоты

`used_bytes` и `data_quota_bytes` возвращаются в байтах. Например, расход пользователей
с месячной квотой можно вывести в гигабайтах:

```python
quotas = await client.stats.quota()
for quota in quotas.data.users:
    if quota.quota_period == "monthly":
        print(
            quota.username,
            f"{quota.used_bytes / 1_000_000_000:.2f} / "
            f"{quota.data_quota_bytes / 1_000_000_000:.2f} GB",
            quota.quota_next_reset_epoch_secs,
        )
```

## Ответы и ревизии

Каждый метод возвращает `APIResponse[T]`:

| Поле | Тип | Назначение |
| --- | --- | --- |
| `data` | `T` | Типизированный результат операции, например `UserInfo` или `list[UserInfo]`. |
| `revision` | `str` | Ревизия конфигурации сервера для этого ответа. |
| `status_code` | `int` | Фактический HTTP-статус ответа. |
| `ok` | `Literal[True]` | Успешно разобранный ответ API. |

Все методы, кроме `config.state()`, возвращают `APIResponse[T]` с обязательной
ревизией. `config.state()` возвращает `NullableRevisionAPIResponse[ConfigStateData]`,
у которого `revision` имеет тип `str | None`: сервер опускает ревизию, когда желаемая
конфигурация ещё не зафиксирована, поэтому проверяйте поле на `None`, прежде чем
использовать его в `If-Match`.

Вложенные данные тоже представлены моделями: `user.links.tls_domains[0].domain`
и `status.runtime.manager.issuance_enabled` доступны проверке типов после проверки
nullable-полей на `None`. Модели импортируются из `telemt.models`.

```python
current = await client.users.get("alice")
await client.users.update(
    "alice",
    PatchUserRequest(max_tcp_conns=30),
    revision=current.revision,
)
```

Аргумент `revision=` передаётся в заголовок `If-Match`. Устаревшая ревизия вызывает
`ConflictError`. Перечитайте состояние и проверьте, остаётся ли изменение актуальным,
прежде чем повторять запрос. Клиент не хранит общую ревизию и не подставляет её автоматически,
поэтому параллельные ответы независимы. WEB-операции используют `runtime_instance`.

Мутации конфигурации и политики доступа дополнительно принимают `runtime_match=` —
непрозрачный токен публикации runtime из `config.state()` (`runtime.runtime_match`) или
из `ConfigValidationData.runtime`, который передаётся в заголовок `If-Runtime-Match`.
SDK проверяет токен до отправки: от 1 до 128 символов, только шестнадцатеричные цифры
и двоеточия. Устаревший токен вызывает `ConflictError` (409 `runtime_conflict`) —
сервер успел применить другую конфигурацию раньше вашей записи.

Новые поля сервера сохраняются в `model_extra`. Для представления, совместимого с JSON,
используйте `model_dump(mode="json", by_alias=True)`. Разделы конфигурации остаются
`dict[str, JsonValue]`, поскольку это расширяемые конфигурационные данные;
известные структуры телеметрии и WEB описаны отдельными моделями.

## Конфигурация и перезагрузка

```python
import asyncio

from telemt.models import PatchConfigRequest, ReloadRequest

current = await client.config.get()
changed = await client.config.update(
    PatchConfigRequest(censorship={"tls_domain": "front.example.com"}),
    revision=current.revision,
    reload=ReloadRequest(mode="drain", timeout_secs=30, failure_policy="rollback"),
)
if changed.data.reload is not None:
    progress = await client.system.wait_reload(
        changed.data.reload.reload_id, timeout=60, poll_interval=1
    )
    print(progress.data.state)
    for warning in progress.data.warnings:
        print(warning)
    if progress.data.deferred_process_fields:
        print("Restart required:", progress.data.deferred_process_fields)
    if progress.data.state != "succeeded":
        raise RuntimeError(progress.data.error or progress.data.state)
```

Для изменения доступны `general`, `timeouts`, `censorship`, `upstreams`, `dc_overrides`,
`web`, `server.listeners`, пять наблюдаемых настроек `server.api`
(`minimal_runtime_enabled`, `minimal_runtime_cache_ttl_ms`, `runtime_edge_enabled`,
`runtime_edge_cache_ttl_ms`, `runtime_edge_top_n`) и `network.dns_overrides`
(пустой список очищает переопределения DNS). Другие ключи `server` и `network`
отклоняются моделью запроса. Проверка на стороне сервера определяет, какие вложенные
параметры можно изменить и каким требуется перезапуск процесса.

HTTP `202` означает принятие операции, а не её завершение. Опрашивайте
`system.reload_status(id)` с интервалом и общим тайм-аутом, подходящими вашему приложению,
до состояния `succeeded`, `rolled_back` или `failed`. Проверяйте `warnings`,
`deferred_process_fields` и `error` в результате. Для отдельной перезагрузки вызовите
`system.reload(ReloadRequest(...))`. Режим `drain` требует `timeout_secs` от 1 до 3600;
режим `instant` не принимает этот параметр.

Изменения применяются сервером асинхронно: watcher публикует новую конфигурацию,
а перезагрузка поколения runtime распространяет её на работающие обработчики. Флаги
`restart_required`, `runtime_reload_required` и `process_restart_required` в ответе
`config.update()` и в `ConfigValidationData.apply` показывают, какие границы должна
пересечь правка, — не прерывайте процесс, пока флаги не сброшены и `config.state()`
не сообщит `comparison.status == "published_match"`.

### Схема, состояние и предварительная проверка конфигурации

```python
schema = await client.config.schema()
print(schema.data.schema_version, len(schema.data.fields))

state = await client.config.state()  # или client.config.state(["network", "access"])
print(state.revision, state.data.desired_status, state.data.comparison.status)

report = await client.config.validate(
    PatchConfigRequest(network={"dns_overrides": ["1.1.1.1"]}),
    revision=state.revision,
)
print(report.data.valid, report.data.changed_paths, report.data.touched_sections)
```

`config.schema()` возвращает метаданные полей конфигурации: пути, значения по умолчанию,
ограничения, политику применения (watcher, reload, эффект) и связанные API-маршруты.

`config.state()` сравнивает желаемую и эффективную конфигурацию: проекции полей,
отличия watcher, перезагрузки и runtime. Параметр `sections` фильтрует разделы; он
принимает непустую последовательность уникальных имён из `general`, `network`,
`server`, `timeouts`, `censorship`, `upstreams`, `dc_overrides`, `web`, `access`,
`logging` и `root`. Только `sections=None` полностью опускает query-параметр; пустая
последовательность, дубликаты и неизвестные имена отклоняются `ValueError` до отправки.

`config.validate()` выполняет предварительную проверку правки без её сохранения:
ничего не фиксируется и не резервируется, проверку можно повторять свободно. Результат
содержит `valid`, `base_revision`, `candidate_revision`, `changed_paths`,
`normalization_effects`, `touched_sections` и `apply` с флагами перезагрузки. При
отклонении сервер возвращает структурированные детали ошибки (см. раздел об ошибках).

### Политика доступа

```python
from telemt.models import AccessPolicyPatch, CidrRateLimitInput

policy = await client.access.get()
print(policy.data.desired, policy.data.published_match)

updated = await client.access.update(
    AccessPolicyPatch(
        user_max_tcp_conns_global_each=64,
        cidr_rate_limits={"203.0.113.0/24": CidrRateLimitInput(up_bps=10_000_000)},
    ),
    revision=policy.revision,
    runtime_match=policy.data.runtime.runtime_match,
)
print(updated.data.changed_paths)
```

`AccessPolicyPatch` — разреженный merge patch из пяти политик: пропущенные поля
не меняются, явный `None` у скаляра восстанавливает значение по умолчанию, явный `None`
у записи `cidr_rate_limits` удаляет правило для этой сети, а `None` вместо всей карты
очищает все правила. Полностью пустая правка отклоняется. Ключи `cidr_rate_limits`
принимают CIDR-префиксы и шаблоны `*4/N`, `*6/N`, `*/N`; каждое значение требует
хотя бы одного положительного направления (`up_bps` или `down_bps` до 100 Гбит/с,
ноль означает «без ограничения»). Ответ содержит желаемый и эффективный снимки,
статус публикации и `changed_paths` (только у PATCH).

## WEB-сессии и жизненный цикл

```python
from telemt.models import CloseRequest, RefsSelector, SessionQuery

status = await client.runtime.web.status()
if status.data.runtime is not None:
    page = await client.runtime.web.sessions(SessionQuery(user="alice", limit=50))
    if page.data.sessions:
        accepted = await client.runtime.web.close_sessions(
            CloseRequest(
                runtime_instance=status.data.runtime.runtime_instance,
                selector=RefsSelector(session_refs=[row.session_ref for row in page.data.sessions]),
            )
        )
        progress = await client.runtime.web.wait_operation(accepted.data.operation_id, timeout=60)
        print(progress.data.state)
```

Для просмотра всех страниц сессий пользователя:

```python
from telemt.models import SessionQuery

async for session in client.runtime.web.iter_sessions(SessionQuery(user="alice", limit=100)):
    print(session.session_ref)
```

Страница сессий содержит до 200 записей. Для следующей страницы передайте
`SessionQuery(cursor=page.data.next_cursor, ...)` с теми же фильтрами. Завершайте обход,
когда `next_cursor` равен `None`. Поля `scan_truncated`, `partial_sessions` и `partial`
описывают ограничения снимка состояния.

Для `pause`, `resume`, `clear_debug` и `reset_carrier_learning` используется
`RuntimeInstanceRequest`, для `drain` — `DrainRequest`. `FilterSelector` выбирает сессии
по фильтрам. `AllSelector` требует, чтобы `runtime.manager.issuance_enabled` был равен
`False`; операторский `pause()` управляет отдельным механизмом допуска. Перед выбором
всех сессий проверьте состояние runtime. Для управляемого завершения текущей работы
используйте `drain()`.

Ссылки на сессии и операции действуют в пределах текущего процесса сервера.
Опрашивайте возвращённый идентификатор операции, чтобы узнать результат:
принятие запроса само по себе не означает завершения. `wait_operation()` считает
терминальными состояния `completed`, `failed` и `cancelled`.

## Обработка ошибок

```python
from telemt import APIError, ConflictError, TransportError

try:
    current = await client.users.get("alice")
    disabled = await client.users.disable("alice", revision=current.revision)
except ConflictError as error:
    print("Conflict:", error.code, error.request_id)
except APIError as error:
    print(error.status_code, error.code, error.message)
except TransportError:
    # Перечитайте состояние сервера перед решением о повторном изменении.
    raise
```

| Исключение | Значение |
| --- | --- |
| `AuthenticationError` | HTTP 401. |
| `PermissionDeniedError` | HTTP 403, включая режим read-only. |
| `NotFoundError` | HTTP 404. |
| `ConflictError` | HTTP 409, включая конфликт ревизий и устаревший токен runtime. |
| `APIError` | Другие ошибки сервера; доступны `status_code`, `code`, `message`, `request_id` и `details`. |
| `RequestTimeoutError` | Тайм-аут HTTPX; наследуется от `TransportError`. |
| `TransportError` | Ошибка сети или транспорта; исходное исключение доступно в `__cause__`. |
| `InvalidResponseError` | Некорректный JSON, формат ответа или структура данных. |

Все исключения SDK наследуются от `TelemtError`. Ошибки моделей запросов вызывают
`pydantic.ValidationError`; недопустимые аргументы маршрутов — `ValueError`, включая
его подкласс `ValidationError`. Отмена асинхронной задачи распространяется без обёртки.

Сервер может добавлять к отклонённому запросу структурированные детали: `APIError.details`
содержит кортеж объектов `FieldIssue` с полями `path`, `code` и `message` (например,
`code="unknown_field"` с путём неизвестного поля у предварительной проверки конфигурации).
Кортеж пуст, когда сервер детали не предоставил.

Два HTTP-статуса могут содержать штатный результат: `health.ready()` возвращает данные
готовности при HTTP 503, а `runtime.web.session()` — `GoneSessionData` при HTTP 410.
Ответ с ошибкой API на этих маршрутах по-прежнему вызывает исключение. Используйте
`isinstance(result.data, GoneSessionData)`, чтобы отличить закрытую сессию от `SessionRow`.

## Совместимость

SDK следует [проекту Telemt](https://github.com/telemt/telemt) и его
[Control API](https://github.com/telemt/telemt/blob/main/docs/Architecture/API/API.md).
Клиент охватывает все 54 операции Control API Telemt **3.5.17** (проверен против
тега `3.5.17`, коммит
[`66708d2866f3f3a4541c4fa67984d408e71a8af4`](https://github.com/telemt/telemt/tree/66708d2866f3f3a4541c4fa67984d408e71a8af4)),
и рассчитан на Telemt 3.5.17 и совместимые выпуски 3.5.x. HTML-страница `/web-status`
и транспортные WEB-эндпоинты находятся за пределами этого API-клиента.

Поддерживаются Python 3.13, 3.14 и 3.15 под Linux и Windows. Необязательные
возможности Telemt могут возвращать данные об отключённой или недоступной функции:
проверяйте `enabled`, `reason`, `data` и `partial`, когда они присутствуют. Сохранение
новых полей помогает при расширении ответов сервера, но не означает гарантированную
совместимость со всеми прошлыми и будущими изменениями API.

Полный перечень методов, типов запросов и ответов доступен в
[справочнике API](https://github.com/Peakora-VPN/telemt-sdk/blob/main/docs/api-reference.md).

## Участие в разработке и поддержка

Сообщения об ошибках и pull request приветствуются. В
[issue](https://github.com/Peakora-VPN/telemt-sdk/issues) укажите версии Python, SDK и Telemt,
минимальный пример и тип исключения или код ошибки Telemt. Удалите заголовки авторизации,
секреты и приватные настройки из публикуемых материалов.

Настройка окружения uv, линтер, проверка типов и тесты описаны в
[CONTRIBUTING.md](https://github.com/Peakora-VPN/telemt-sdk/blob/main/CONTRIBUTING.md).

<p align="center"><strong>🤝 Спонсор проекта — Peakora VPN</strong></p>
<p align="center">
  <a href="https://peakora.network/">
    <img src="https://peakora.network/social-preview.png" width="600" alt="Peakora VPN — интернет в вашем ритме">
  </a>
</p>
<p align="center">
  Защищённый доступ в интернет и к AI-сервисам с подключением через Telegram.<br>
  <a href="https://peakora.network/">Подробнее о Peakora →</a>
</p>

## Лицензия

[MIT](https://github.com/Peakora-VPN/telemt-sdk/blob/main/LICENSE) © 2026 Peakora-VPN.
