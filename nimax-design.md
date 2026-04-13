# nimax — Design Document

> A clean-room re-implementation of betamax for [niquests](https://github.com/jawah/niquests).
> Working title: **nimax**

---

## 1. Motivation

`betamax` is a VCR-style HTTP recording library for the `requests` library.
`niquests` is a drop-in `requests` replacement that adds HTTP/2, HTTP/3,
multiplexed connections, lazy responses, and `AsyncSession`. Betamax is
fundamentally incompatible with niquests because:

| Betamax assumption | Niquests reality |
|---|---|
| `send()` returns a complete `Response` immediately | `Response` may be **lazy** — attributes unresolved until awaited or `gather()`d |
| One request in-flight per `send()` | `multiplexed=True` sends many before any resolve |
| Only synchronous sessions | `AsyncSession` with `async def send()` |
| HTTP/1.1 headers only | HTTP/2 pseudo-headers, QUIC trailers, protocol negotiation metadata |
| `BaseAdapter` / `HTTPAdapter` from `requests` | Same API surface in niquests but wraps `urllib3.future` (not urllib3) |

A clean-room re-write allows us to design natively for these constraints
rather than patching around them.

---

## 2. Betamax Architecture (reference)

Understanding what we are replacing:

```
Session
  └── BetamaxAdapter (mounted at "http://" and "https://")
        ├── cassette: Cassette | None
        ├── http_adapter: HTTPAdapter          ← real network I/O
        ├── send(request) → Response
        │     1. find matching Interaction in cassette
        │     2a. match found  → build Response from cassette data
        │     2b. no match + recording allowed → send_and_record()
        │     2c. no match + recording disabled → raise BetamaxError
        └── send_and_record()
              1. delegate to http_adapter.send()
              2. cassette.save_interaction(request, response)
```

**Cassette file format** (JSON, default):

```json
{
  "http_interactions": [
    {
      "request":  { "method": "GET", "uri": "...", "headers": {}, "body": null },
      "response": { "status": {"code": 200, "message": "OK"},
                    "headers": {}, "body": {"string": "..."} },
      "recorded_at": "2024-01-01T00:00:00"
    }
  ],
  "recorded_with": "betamax/0.8.2"
}
```

**Record modes**: `once` · `none` · `new_episodes` · `all`
**Matchers**: `method` · `uri` · `host` · `path` · `query` · `headers` · `body`
**Serializers**: JSON (built-in) · YAML (third-party)

---

## 3. Key Design Challenges

### 3.1 Lazy Responses

Niquests returns a `Response` that may not have its body resolved yet.
Recording must occur **after** the response is fully consumed, not in `send()`.

Strategy: hook into niquests' **event hook system** (`response` hook) to
trigger the record step once the response is fully materialized.

### 3.2 Multiplexed Sessions

`Session(multiplexed=True)` sends N requests before any response resolves.
`gather(*responses)` then resolves them all.

Strategy: the adapter intercepts `send()` for each request and records
**pending** interaction slots. The `gather()` step triggers actual
serialization once responses are available. We must wrap `Session.gather()`
or hook into the response lifecycle.

### 3.3 Async Sessions

`AsyncSession` has `async def send()`. The adapter shim must expose both
sync `send()` and `async def send()`.

Strategy: `NimaxAdapter` provides both methods. The async path is a coroutine
that awaits the real adapter and writes to the cassette.

### 3.4 Protocol Metadata

Cassettes should optionally preserve the negotiated protocol (`HTTP/1.1`,
`HTTP/2`, `HTTP/3`) so replay can assert the same protocol was used.

---

## 4. Proposed Architecture

```
NimaxRecorder                  ← replaces Betamax class; wraps Session
  ├── use_cassette(name, **kw) → context manager
  └── _mount_adapter(session)

NimaxAdapter(BaseAdapter)      ← mounted at "http://" + "https://"
  ├── cassette: Cassette | None
  ├── _real: HTTPAdapter        ← niquests HTTPAdapter for live I/O
  ├── send(PreparedRequest, **kw) → Response
  └── async asend(PreparedRequest, **kw) → Response

Cassette
  ├── record_mode: RecordMode
  ├── matchers: list[BaseMatcher]
  ├── serializer: BaseSerializer
  ├── interactions: list[Interaction]
  ├── find_match(request) → Interaction | None
  ├── save_interaction(request, response) → None
  ├── load() / save()
  └── sanitize(placeholders)

Interaction
  ├── request: SerializedRequest
  ├── response: SerializedResponse
  ├── recorded_at: datetime
  ├── protocol: str | None        ← NEW: "HTTP/2", "HTTP/3", etc.
  └── used: bool                  ← for "once" mode exhaustion tracking

RecordMode(enum)
  NONE · ONCE · NEW_EPISODES · ALL

BaseMatcher (ABC)
  name: str
  match(recorded: SerializedRequest, live: PreparedRequest) → bool

BaseSerializer (ABC)
  extension: str
  serialize(cassette_data: dict) → str
  deserialize(raw: str) → dict
```

### 4.1 Session Wrapping

```python
with NimaxRecorder(session).use_cassette("my_test") as recorder:
    resp = session.get("https://example.com")
```

For async:

```python
async with NimaxRecorder(async_session).use_cassette("my_test") as recorder:
    resp = await async_session.aget("https://example.com")
```

`NimaxRecorder` mounts `NimaxAdapter` on enter and restores original adapters
on exit. It also wraps `session.gather` to trigger deferred interaction saves.

### 4.2 Lazy Response Handling

`NimaxAdapter.send()` registers a `response` event hook on the prepared
request **before** delegating to the real adapter:

```python
def send(self, request, **kwargs):
    if self.cassette.should_record(request):
        request.hooks["response"].append(self._on_response_received)
    elif (interaction := self.cassette.find_match(request)):
        return self._build_response(request, interaction)
    else:
        raise CannotSendRequest(request)
    return self._real.send(request, **kwargs)

def _on_response_received(self, response, **kwargs):
    # Called after body is available
    self.cassette.save_interaction(response.request, response)
```

### 4.3 Multiplexed Session Handling

For multiplexed sessions, `send()` returns immediately with a lazy
`Response`. Actual recording happens in a wrapped `gather()`:

```python
class NimaxRecorder:
    def _patch_gather(self, session):
        original_gather = session.gather

        def patched_gather(*responses, **kwargs):
            result = original_gather(*responses, **kwargs)
            for resp in responses:
                if resp in self._pending_record:
                    self.cassette.save_interaction(resp.request, resp)
            return result

        session.gather = patched_gather
```

### 4.4 Async Adapter

```python
class NimaxAdapter(BaseAdapter):
    def send(self, request, **kw):
        # sync path
        ...

    async def asend(self, request, **kw):
        # async path — await self._real.asend(...)
        ...
```

---

## 5. Cassette Format

Extends betamax's format with a `protocol` field and a schema version.
Backwards-compatible with betamax cassettes (protocol field optional).

```json
{
  "nimax_version": "0.1.0",
  "http_interactions": [
    {
      "request": {
        "method": "GET",
        "uri": "https://example.com/api",
        "headers": { "User-Agent": ["niquests/3.x"] },
        "body": null
      },
      "response": {
        "status": { "code": 200, "message": "OK" },
        "headers": { "Content-Type": ["application/json"] },
        "body": { "string": "{\"key\": \"value\"}" },
        "protocol": "HTTP/2"
      },
      "recorded_at": "2026-04-12T10:00:00Z"
    }
  ]
}
```

---

## 6. Record Modes

| Mode | Behaviour |
|---|---|
| `ONCE` | Record on first run; replay thereafter. Error if cassette exists and request has no match. |
| `NONE` | Never record. All requests must match a stored interaction. |
| `NEW_EPISODES` | Replay existing matches; record unmatched requests. |
| `ALL` | Re-record every interaction. Replaces cassette on each run. |

---

## 7. Matchers

Built-in matchers (all from betamax, re-implemented):

- `method` — HTTP verb
- `uri` — full URI including query string
- `host` — hostname only
- `path` — path component only
- `query` — query string (order-insensitive)
- `headers` — subset of request headers
- `body` — raw body bytes

New matchers added for niquests:

- `protocol` — assert `HTTP/1.1` / `HTTP/2` / `HTTP/3` match

Custom matchers registered via:

```python
NimaxRecorder.register_matcher(MyMatcher)
```

---

## 8. Serializers

Built-in:

- `json` — compact JSON (default)
- `pretty_json` — indented JSON for human-readable cassettes

Third-party extension point: `BaseSerializer` ABC with `serialize()` /
`deserialize()` methods. Register via:

```python
NimaxRecorder.register_serializer(YAMLSerializer)
```

---

## 9. pytest Integration

```python
# conftest.py
import pytest
from nimax.pytest_plugin import nimax_fixture

@pytest.fixture
def betamax_session(nimax_session):
    return nimax_session
```

The plugin provides:

- `nimax_session` fixture — a `niquests.Session` with `NimaxAdapter` mounted
- `nimax_async_session` fixture — an `AsyncSession` variant
- Auto-naming cassettes by test module + function name
- `nimax_parametrized_recorder` for parameterised tests

Configuration via `conftest.py` or `pyproject.toml`:

```toml
[tool.nimax]
cassette_library_dir = "tests/cassettes"
default_cassette_name = "{module}/{test}"
record_mode = "once"
match_on = ["method", "uri"]
```

---

## 10. Placeholder / Sanitization

Sensitive values (API keys, tokens) are replaced before cassette writes:

```python
with NimaxRecorder(session).use_cassette(
    "auth_test",
    placeholders=[
        Placeholder(placeholder="<API_KEY>", replace=os.environ["API_KEY"])
    ]
):
    ...
```

On record: `os.environ["API_KEY"]` → `<API_KEY>` in cassette.
On replay: `<API_KEY>` → `os.environ["API_KEY"]` in reconstructed response.

---

## 11. WebSocket Recording

### 11.1 Conceptual Model

A WebSocket session has two distinct phases:

1. **Handshake** — an HTTP `GET` with `Upgrade: websocket`. This is a normal
   HTTP interaction and is recorded using the existing `http_interactions` model.
2. **Frame exchange** — a bidirectional stream of frames after the upgrade.
   This requires a separate `websocket_sessions` track in the cassette.

In niquests, WebSocket is accessed via `resp.extension` after calling
`session.ws_connect()` (or equivalent). Recording wraps that extension object
in a proxy that intercepts `send_payload()` and `next_payload()` calls.

### 11.2 Frame Model

Each recorded frame has:

| Field | Type | Description |
|---|---|---|
| `direction` | `"send"` \| `"recv"` | Client-to-server or server-to-client |
| `type` | `"text"` \| `"binary"` \| `"ping"` \| `"pong"` \| `"close"` | WS frame opcode |
| `payload` | `str` \| `bytes` \| `null` | Frame payload (base64 for binary) |
| `offset_ms` | `int` | Milliseconds since handshake (optional; for timing replay) |
| `close_code` | `int` \| `null` | Only on `close` frames (e.g. 1000 = Normal Closure) |
| `close_reason` | `str` \| `null` | Only on `close` frames |

### 11.3 Cassette Format Extension

```json
{
  "nimax_version": "0.1.0",
  "http_interactions": [],
  "websocket_sessions": [
    {
      "uri": "wss://example.com/ws",
      "handshake_recorded_at": "2026-04-12T10:00:00Z",
      "protocol": "HTTP/1.1",
      "frames": [
        { "direction": "send", "type": "text",   "payload": "hello",   "offset_ms": 0   },
        { "direction": "recv", "type": "text",   "payload": "world",   "offset_ms": 48  },
        { "direction": "send", "type": "binary", "payload": "aGVsbG8=","offset_ms": 120 },
        { "direction": "recv", "type": "close",  "payload": null,
          "close_code": 1000, "close_reason": "Normal Closure",        "offset_ms": 200 }
      ]
    }
  ]
}
```

Multiple WS sessions in one cassette are supported (matched by URI, same as
HTTP interactions).

### 11.4 Architecture

```
WebSocketExtensionProxy
  ├── _extension: real niquests WS extension object
  ├── _session: WebSocketSession (in cassette)
  ├── send_payload(payload) → None
  │     record Frame(direction="send", ...)
  │     delegate to _extension.send_payload()
  ├── next_payload() → str | bytes
  │     if replaying: pop next recv Frame from _session, return its payload
  │     if recording: call _extension.next_payload(), record Frame, return
  ├── ping() → None          (recorded as ping frame; replayed as no-op)
  └── close() → None         (records close frame; saves session to cassette)

WebSocketSession
  ├── uri: str
  ├── protocol: str
  ├── handshake_recorded_at: datetime
  ├── frames: list[Frame]
  └── cursor: int            ← replay position for next recv frame
```

`NimaxRecorder` wraps `session.ws_connect()` (or the equivalent call) to
intercept the returned response. On the `response` hook, if the response is a
WebSocket upgrade (status 101), the recorder replaces `resp.extension` with a
`WebSocketExtensionProxy`.

```python
def _on_response_received(self, response, **kwargs):
    if response.status_code == 101:  # WebSocket upgrade
        ws_session = self.cassette.find_or_create_ws_session(response.url)
        response.extension = WebSocketExtensionProxy(
            extension=response.extension,
            ws_session=ws_session,
            record_mode=self.cassette.record_mode,
        )
    else:
        self.cassette.save_interaction(response.request, response)
```

### 11.5 Replay Behaviour

On replay, `next_payload()` pops the next `recv`-direction frame from
`WebSocketSession.frames[cursor:]`. `send_payload()` can optionally validate
that the sent payload matches the recorded `send` frame at the same position
(controlled by a `strict_send` option — default `False` to avoid brittleness).

`ping()` and `pong` frames are replayed as no-ops by default; setting
`replay_pings=True` causes them to be re-emitted on the proxy.

### 11.6 Async Support

`WebSocketExtensionProxy` mirrors the sync/async split in `NimaxAdapter`:

```python
class WebSocketExtensionProxy:
    def send_payload(self, payload): ...
    async def asend_payload(self, payload): ...

    def next_payload(self): ...
    async def anext_payload(self): ...

    def close(self): ...
    async def aclose(self): ...
```

### 11.7 Record Modes for WebSocket

| Mode | Behaviour |
|---|---|
| `ONCE` | Record full frame sequence on first run; replay thereafter |
| `NONE` | Replay only; error if URI has no recorded session |
| `NEW_EPISODES` | Replay known URIs; record new ones |
| `ALL` | Re-record every frame sequence on each run |

### 11.8 WebSocket Design Decisions

1. **Partial frame sequences** — if the test closes the socket early and not
   all recorded frames are consumed, replay raises `CannotEjectCassette`.
   Unconsumed frames indicate an incomplete test or a behavioural regression.

2. **Binary payload encoding** — delegated to the serializer. The frame `type`
   field (`"text"` vs `"binary"`) is the discriminator; no user flag needed.
   The default JSON serializer base64-encodes `binary` frames and stores `text`
   frames as plain UTF-8 strings.

3. **Multiple connections to same URI** — disambiguated via an explicit
   `nimax_label` parameter on `ws_connect()`. The cassette matches sessions by
   `(uri, label)`. Unlabelled connections to a unique URI work without a label;
   a second connection to the same URI without a label raises at record time.

---

## 12. Out of Scope (v0.1)

- SSE (Server-Sent Events) recording
- YAML serializer (first-party; kept as a third-party extension point)
- `betamax-matchers` compatibility shim

---

## 13. Migration from betamax

For users already on betamax with `requests`, switching to nimax + niquests:

1. `pip install niquests nimax`
2. Replace `import requests` → `import niquests as requests`
3. Replace `from betamax import Betamax` → `from nimax import NimaxRecorder`
4. Replace `Betamax(session)` → `NimaxRecorder(session)`
5. Existing JSON cassettes are forward-compatible (no `protocol` field = HTTP/1.1 assumed)
6. pytest: replace `betamax_session` fixture with `nimax_session`

---

## 14. Design Decisions

1. **Cassette name collision in multiplexed mode** — interactions are matched
   by content (matchers), not position. On replay, nimax finds the first
   unmatched stored interaction satisfying all configured matchers, regardless
   of cassette order. Cassettes are not sorted on save; insertion order is
   preserved for readability but is not load-bearing.

2. **`once` mode + lazy responses** — on cassette eject, nimax force-consumes
   any pending lazy responses before writing the cassette file. This prevents
   half-written cassettes that cause confusing match failures on the next run.
   An unconsumed response body at eject time is considered a test smell.

3. **Protocol downgrade on replay** — nimax raises `ProtocolMismatch` when a
   cassette recorded `HTTP/2` or `HTTP/3` but the replayed response negotiated
   a lower protocol. Set `allow_protocol_downgrade=True` on `use_cassette()` to
   suppress the error. Applies to both HTTP interactions and WebSocket
   handshakes.

4. **Thread safety** — in-memory cassette state (`interactions`, WS `cursor`)
   is protected by a `threading.Lock`. File-level isolation is the test
   runner's responsibility; the pytest plugin names cassettes
   `{module}/{test}` by default, ensuring each parallel worker uses a distinct
   file. File locking is not provided.
