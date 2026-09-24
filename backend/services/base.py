"""
Base HTTP client for all external API services.
"""

import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class BaseAPIClient:
    """Shared HTTP client with retry and error handling."""

    def __init__(self, base_url: str, headers: Optional[dict] = None, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.headers = headers or {}
        self.timeout = timeout

    async def _get(self, endpoint: str, params: Optional[dict] = None) -> Optional[dict]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} from {url}: {e.response.text[:200]}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request failed for {url}: {e}")
            return None

    async def _post(self, endpoint: str, data: Optional[dict] = None, json_body: Optional[dict] = None) -> Optional[dict]:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, data=data, json=json_body, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} from {url}: {e.response.text[:200]}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request failed for {url}: {e}")
            return None
