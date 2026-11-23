"""POST one finished RunBundle to the Spring API. A 409 means the run already exists, which counts as done."""

from __future__ import annotations

import httpx
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

from .config import admin_key, api_url

RETRY_WAIT = wait_exponential(multiplier=1, exp_base=4)  # tests replace this with wait_none()


class ApiError(RuntimeError):
    def __init__(self, status: int, body: str):
        super().__init__(f"API returned {status}: {body[:300]}")
        self.status_code = status


def _transient(exc: BaseException) -> bool:
    if isinstance(exc, ApiError):
        return exc.status_code == 429 or exc.status_code >= 500
    return isinstance(exc, (httpx.TimeoutException, httpx.ConnectError))


async def post_bundle(client: httpx.AsyncClient, bundle: dict) -> str:
    """Returns "created" (201) or "exists" (409)."""
    async for attempt in AsyncRetrying(
        retry=retry_if_exception(_transient), stop=stop_after_attempt(4), wait=RETRY_WAIT, reraise=True
    ):
        with attempt:
            r = await client.post(
                f"{api_url()}/api/admin/runs", json=bundle, headers={"X-Admin-Key": admin_key()}, timeout=30
            )
            if r.status_code == 201:
                return "created"
            if r.status_code == 409:
                return "exists"
            raise ApiError(r.status_code, r.text)
    raise RuntimeError("unreachable")
