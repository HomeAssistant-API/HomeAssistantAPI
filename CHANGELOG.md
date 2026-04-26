# HomeAssistant-API v6.0 Changelog

## Breaking Changes
A lot has changed in this version. A lot went into modernising and standardizing the interfaces of the clients.
As such, many of the previous paradigms have changed. If you run into any bugs or issues, please let us know.
### Minimum Python version raised to 3.11
Python 3.9 and 3.10 are no longer supported.

### Client classes restructured
The old `Client` class (which combined sync and async via a `use_async` flag) has been removed. There are now four distinct client classes:

| Old | New |
|---|---|
| `Client(use_async=False)` | `Client` |
| `Client(use_async=True)` | `AsyncClient` |
| `WebsocketClient` (sync) | `WebsocketClient` |
| — | `AsyncWebsocketClient` (new) |

Async client methods no longer have the `async_` prefix — e.g. `async_get_states()` is now just `get_states()` on `AsyncClient`.

### Models split into Base/Sync/Async variants
`Domain`, `Entity`, `Group`, `Service`, and `Event` now have three variants each:
- **`Base*`** — plain data, no client reference
- **`*`** (e.g. `Domain`) — sync, bound to `Client`
- **`Async*`** (e.g. `AsyncDomain`) — async, bound to `AsyncClient`

### Processing module rewritten
The decorator-based `@Processing.processor(mimetype)` registry has been replaced with simple dict-based MIME dispatch and separate `sync`/`async` entry points. Custom processor registration and the `decode_bytes` parameter have been removed.

### Build system moved from Poetry to uv + hatchling
`poetry.lock` is removed. The project now uses `uv` for dependency management and `hatchling` as the build backend.

### Type checker changed from mypy to zuban

## New Features

### WebSocket API support (sync & async)
Full WebSocket client implementation for both sync (`WebsocketClient`) and async (`AsyncWebsocketClient`) with support for:
- **Config entries** — get, disable, enable, ignore flow, subentries, subscribe
- **Entity registry** — list, get, update, remove entries
- **Events** — subscribe, fire, and listen
- **Services** — trigger with full domain/service routing
- **Templates** — render and subscribe to template updates

### Entity registry models
New models: `EntityRegistryEntry`, `EntityRegistryEntryExtended`, `EntityRegistryUpdateResult`.

### Configurable WebSocket max message size
WS clients accept a `max_size` parameter (default 16 MB) to handle large responses like full entity registry lists.

## Improvements

- Unified method signatures across all four client classes for consistency
- Expanded ruff lint rules to `ALL` (from just E, F, W)
- Test coverage improved to ~99%
- Modernized type annotations throughout
- Response content is now read lazily, eliminating internal `_buffer` access hacks
- Migrated from `requests`/`aiohttp`/`websockets` to `niquests`, for modernization and performance.
