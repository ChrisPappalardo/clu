from __future__ import annotations

import time

import httpx


DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=30.0, write=20.0, pool=20.0)


def get_json(
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    retries: int = 2,
    timeout: httpx.Timeout = DEFAULT_TIMEOUT,
) -> dict:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                response = client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError) as exc:
            last_error = exc
            if attempt == retries:
                break
            time.sleep(1.5 * (attempt + 1))
    assert last_error is not None
    raise last_error
