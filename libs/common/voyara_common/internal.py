"""Communication inter-services.

Les endpoints `/internal/*` ne sont jamais exposés par le gateway : ils servent
uniquement aux appels service → service et sont protégés par une clé partagée
(header `X-Internal-Api-Key`).
"""

from typing import Any

import httpx
from fastapi import Header, HTTPException, status

from voyara_common.config import get_common_settings

INTERNAL_HEADER = "X-Internal-Api-Key"


def require_internal_key(
    x_internal_api_key: str = Header(..., alias=INTERNAL_HEADER),
) -> None:
    if x_internal_api_key != get_common_settings().INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clé interne invalide",
        )


def internal_headers() -> dict[str, str]:
    return {INTERNAL_HEADER: get_common_settings().INTERNAL_API_KEY}


class ServiceClient:
    """Petit client HTTP pour appeler les endpoints internes d'un autre service."""

    def __init__(self, base_url: str, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.base_url}{path}", params=params, headers=internal_headers()
            )
            resp.raise_for_status()
            return resp.json()

    async def post(self, path: str, json: Any = None, params: dict[str, Any] | None = None) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}{path}", json=json, params=params, headers=internal_headers()
            )
            resp.raise_for_status()
            return resp.json()
