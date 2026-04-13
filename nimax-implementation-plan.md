# nimax Implementation Plan

Delta between `nimax-design.md` and the current `pytest-niquests-cassettes` package.

---

## Module Structure (new)

```
src/pytest_niquests_cassettes/
  __init__.py          ← add NimaxRecorder, RecordMode, Placeholder, BaseMatcher, BaseSerializer
  plugin.py            ← add nimax_session / nimax_async_session, pyproject.toml config
  _record_mode.py      ← NEW: RecordMode enum (NONE, ONCE, NEW_EPISODES, ALL)
  _placeholders.py     ← NEW: Placeholder dataclass + apply/restore helpers
  _matchers.py         ← NEW: BaseMatcher ABC + 8 concrete matchers
  _serializers.py      ← NEW: BaseSerializer ABC + JSONSerializer + YAMLSerializer
  _websocket.py        ← NEW: Frame, WebSocketSession, 4 extension proxies
  _cassette.py         ← REWRITE: Interaction dataclass, matcher-based lookup, new format
  _adapter.py          ← NEW: NimaxRecorder (class-level monkey-patch wrapper)
```

---

## 1. RecordMode enum (`_record_mode.py`)

Replace `record: bool` with:

| Mode | Behaviour |
|---|---|
| `NONE` | Never record; error on no match |
| `ONCE` | Record if cassette file absent; replay if present; error on match miss |
| `NEW_EPISODES` | Replay known interactions; record unmatched |
| `ALL` | Re-record every interaction |

CLI mapping: `--record` → `ALL`, no flag → `ONCE`.

---

## 2. Matcher system (`_matchers.py`)

```
BaseMatcher(ABC)
  name: ClassVar[str]
  match(recorded: dict, live: PreparedRequest) → bool

Concrete: MethodMatcher, URIMatcher, HostMatcher, PathMatcher,
          QueryMatcher, HeadersMatcher, BodyMatcher, ProtocolMatcher
```

`NimaxRecorder._matchers` is a `ClassVar[dict[str, type[BaseMatcher]]]`. Lookup by
name string from `--cassette-match-on`. Default: `["method", "path"]`.

`NimaxRecorder.register_matcher(cls)` adds to class-level dict.

---

## 3. Serializer system (`_serializers.py`)

```
BaseSerializer(ABC)
  extension: ClassVar[str]
  serialize(data: dict) → str
  deserialize(raw: str) → dict

JSONSerializer  — extension = "json"
YAMLSerializer  — extension = "yaml"  (backward-compat default in plugin)
```

Plugin default: `YAMLSerializer` (keeps existing `cassettes/session.yaml` working).
`NimaxRecorder.use_cassette()` default: `JSONSerializer`.

`NimaxRecorder.register_serializer(cls)` adds to class-level dict.

---

## 4. Cassette format (`_cassette.py`)

New on-disk format (mirrors `nimax-design.md` §5):

```json
{
  "nimax_version": "0.1.0",
  "http_interactions": [
    {
      "request":  { "method": "GET", "uri": "...", "headers": {}, "body": null },
      "response": { "status": {"code": 200, "message": "OK"},
                    "headers": {}, "body": {"string": "..."}, "protocol": null },
      "recorded_at": "2026-04-12T10:00:00Z"
    }
  ],
  "websocket_sessions": [...]
}
```

**Legacy migration** (auto-detected on `_load`):
- `interactions` key → treated as `http_interactions`
- `status: 200` → `{"code": 200, "message": "OK"}`
- `body: "..."` → `{"string": "..."}`
- `request.url` → `request.uri`

Headers stored as `{ "Content-Type": ["application/json"] }` (list values).

**Interaction lookup**: linear scan with matcher objects, `Interaction.used` flag.
FIFO semantics for multiple identical interactions preserved by scan order.

**Thread safety**: `threading.Lock` guards `_interactions` and `_websocket_sessions`.

---

## 5. Placeholder system (`_placeholders.py`)

```python
@dataclass
class Placeholder:
    placeholder: str   # stored in cassette
    replace: str       # real value in env

apply_placeholders(text, placeholders)   # real → placeholder (before save)
restore_placeholders(text, placeholders) # placeholder → real (after load)
```

Applied at the serialized-string level, before write and after read.

---

## 6. WebSocket frame model (`_websocket.py`)

`Frame` dataclass gains `type`, `offset_ms`, `close_code`, `close_reason`:

```python
@dataclass
class Frame:
    direction: str        # "send" | "recv"
    type: str             # "text" | "binary" | "ping" | "pong" | "close"
    payload: str | None
    offset_ms: int = 0
    close_code: int | None = None
    close_reason: str | None = None
```

`WebSocketSession` dataclass holds `uri`, `protocol`, `handshake_recorded_at`, `frames`.

The four extension proxy classes (`FakeExtension`, `AsyncFakeExtension`,
`RecordingExtension`, `AsyncRecordingExtension`) remain but use `Frame` internally.
`RecordingExtension.next_payload` captures `offset_ms` via `time.monotonic()`.

---

## 7. NimaxRecorder (`_adapter.py`)

```python
class NimaxRecorder:
    _matchers:    ClassVar[dict[str, type[BaseMatcher]]]
    _serializers: ClassVar[dict[str, type[BaseSerializer]]]

    def __init__(self, session: Session | AsyncSession) -> None: ...

    @classmethod
    def register_matcher(cls, matcher: type[BaseMatcher]) -> None: ...

    @classmethod
    def register_serializer(cls, serializer: type[BaseSerializer]) -> None: ...

    @contextlib.contextmanager
    def use_cassette(
        self,
        name: str,
        *,
        cassette_dir: Path | str = "cassettes",
        record_mode: RecordMode = RecordMode.ONCE,
        match_on: Iterable[str] = ("method", "path"),
        serializer: BaseSerializer | None = None,
        placeholders: list[Placeholder] | None = None,
    ) -> Generator[Cassette, None, None]: ...
```

Internally patches `niquests.Session.send` and `niquests.AsyncSession.send`
class-wide (same approach as current `Cassette.__enter__`).

---

## 8. pytest plugin (`plugin.py`)

**Record mode**: `--record` → `RecordMode.ALL`; default → `RecordMode.ONCE`.
`--record-mode` option added for explicit control.

**Existing `cassette` fixture**: unchanged name, unchanged scope (`session`),
now uses `RecordMode` + `NimaxRecorder` internally.

**New fixtures**:

```python
@pytest.fixture
def nimax_session(request) -> Generator[Session, None, None]:
    """Per-test session with auto-named cassette: {module}/{test}."""

@pytest_asyncio.fixture
async def nimax_async_session(request) -> AsyncGenerator[AsyncSession, None]:
    """Per-test async session with auto-named cassette."""
```

**pyproject.toml config** (`[tool.nimax]`):

```toml
[tool.nimax]
cassette_library_dir = "tests/cassettes"
default_cassette_name = "{module}/{test}"
record_mode = "once"
match_on = ["method", "uri"]
```

Read via `tomllib` (Python 3.11+). CLI options override `pyproject.toml`.

---

## 9. Breaking changes

- Cassette saved in new format (old YAML cassettes are auto-migrated on read,
  but saved back in new format on next record run).
- Default mode is now `ONCE` (not `ALL`). Re-recording requires `--record` or
  `--record-mode=all`.
- `Cassette(path, record=True)` still accepted but deprecated in favour of
  `record_mode=RecordMode.ALL`.

---

## 10. Out of scope for this iteration

- `NimaxAdapter(BaseAdapter)` mounting (WS scheme support uncertain; monkey-patch
  kept as implementation detail)
- `nimax_parametrized_recorder` fixture
- `CannotEjectCassette` on unconsumed WS frames
- Protocol downgrade detection (`ProtocolMismatch`)
- `allow_protocol_downgrade` option
- `gather()` wrapping for multiplexed sessions
