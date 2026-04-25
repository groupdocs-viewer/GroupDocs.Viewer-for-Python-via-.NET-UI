# Custom Cache — TTL Wrapper

Compose a TTL layer on top of any existing `FileCache` impl. Pattern: the wrapper itself satisfies `FileCache`, so it can be passed to `create_app(cache=...)` like any built-in.

## The protocol

```python
class FileCache(Protocol):
    async def try_get(self, cache_key: str, file_path: str) -> bytes | None: ...
    async def set(self, cache_key: str, file_path: str, data: bytes) -> None: ...
    async def remove(self, file_path: str) -> None: ...
```

## What this example does

`TTLCache` keeps an in-memory map of `(file_path, cache_key) → timestamp`. On `try_get` it checks freshness; on `set` it records the timestamp and forwards. On `remove` it drops timestamps for the file.

The inner cache is `InMemoryCache` here, but it could equally be `LocalFileCache` or `RedisCache` — `TTLCache` doesn't care.

## Run

```bash
pip install groupdocs-viewer-net-ui uvicorn
python main.py
# → http://127.0.0.1:8080/viewer/
```

Render a page — second request hits the cache. Wait 5 minutes, render again — re-renders.

## When to use this

When source documents can change underneath the viewer and you want the cache to invalidate eventually even without an explicit `remove(file_path)` call. For documents that never change, a plain `LocalFileCache` is simpler.
