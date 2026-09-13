from typing import Any

import httpx

from app.integrations.contracts import AdapterError
from app.models import IntegrationProvider


class VendorHttpClient:
    def __init__(
        self,
        provider: IntegrationProvider,
        base_url: str,
        headers: dict[str, str],
        timeout: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.provider = provider
        self.client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers=headers,
            timeout=timeout,
            transport=transport,
        )

    async def request(
        self, method: str, path: str, *, params: dict[str, Any] | None = None, json: Any = None
    ) -> Any:
        try:
            response = await self.client.request(method, path, params=params, json=json)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise AdapterError(self.provider, "Integration is unavailable", retryable=True) from exc
        if response.is_error:
            retryable = response.status_code == 429 or response.status_code >= 500
            raise AdapterError(
                self.provider,
                f"Integration returned HTTP {response.status_code}",
                retryable=retryable,
            )
        if response.status_code == 204 or not response.content:
            return {}
        try:
            return response.json()
        except ValueError as exc:
            raise AdapterError(self.provider, "Integration returned invalid JSON") from exc

    async def close(self) -> None:
        await self.client.aclose()
