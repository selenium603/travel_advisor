"""Ctrip Wendao natural-language travel search client."""

import logging
import json
import subprocess
import sys
from typing import Optional
import asyncio

import httpx

from backend.config.settings import settings

logger = logging.getLogger(__name__)


class WendaoClient:
    URL = "https://wendao-skill-prod.ctrip.com/skill/query"

    async def query(self, question: str) -> str:
        if not settings.wendao_api_key:
            return ""

        body = {"token": settings.wendao_api_key, "query": question}
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(self.URL, json=body)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning("Wendao returned HTTP %s", exc.response.status_code)
            return ""
        except httpx.RequestError as exc:
            if sys.platform == "win32":
                raw = await asyncio.to_thread(self._query_with_powershell, body)
                if raw:
                    return self._extract_text(raw)
            # Do not log the request body: it contains the token.
            logger.warning("Wendao request failed: %s", type(exc).__name__)
            return ""

        return self._extract_text(response.text)

    @classmethod
    def _query_with_powershell(cls, body: dict) -> str:
        """Use Windows' HTTP stack when Python's connection is rejected."""
        script = (
            "[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false); "
            "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false); "
            "$body = [Console]::In.ReadToEnd(); "
            "try { $response = Invoke-WebRequest -Uri '"
            + cls.URL
            + "' -Method Post -ContentType 'application/json; charset=utf-8' "
            "-Body $body -TimeoutSec 45; "
            "[Console]::Out.Write($response.Content) } catch { exit 1 }"
        )
        try:
            process = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                input=json.dumps(body, ensure_ascii=False),
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=50,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return ""
        return process.stdout.strip() if process.returncode == 0 else ""

    @staticmethod
    def _extract_text(raw: str) -> str:
        try:
            payload = json.loads(raw)
        except ValueError:
            return raw.strip()

        if isinstance(payload, str):
            return payload.strip()
        if isinstance(payload, dict):
            if payload.get("error"):
                logger.warning("Wendao returned an error")
                return ""
            result = payload.get("result")
            if isinstance(result, str):
                return result.strip()

        logger.warning("Wendao returned an unsupported response format")
        return ""

    async def search_hotels(
        self, destination: str, check_in: str, check_out: str, guests: int,
        request_context: Optional[str] = None,
    ) -> str:
        if request_context:
            return await self.query(
                "请根据以下旅行需求查询酒店，列出名称、房型、入住日期、每晚价格及币种、"
                f"评分和预订链接；只报告实际查到的信息：{request_context}"
            )
        return await self.query(
            f"请查询{destination}的酒店，入住日期{check_in}，退房日期{check_out}，"
            f"入住人数{guests}人。请列出酒店名称、房型、每晚价格及币种、评分和预订链接；"
            "只报告实际查到的信息，缺失字段请明确说明。"
        )

    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str],
        travelers: int,
        cabin_class: str,
        request_context: Optional[str] = None,
    ) -> str:
        trip = f"去程{departure_date}，返程{return_date}" if return_date else f"出发日期{departure_date}"
        context = f" 其他旅行偏好：{request_context}" if request_context else ""
        return await self.query(
            f"请查询从{origin}到{destination}的机票，{trip}，{travelers}位乘客，"
            f"{cabin_class}舱。请列出航司、航班号、起降时间、价格及币种和预订链接；"
            "只报告实际查到的具体航班和可预订信息。若没有查到可核实的报价，"
            "请说明当前查询无可核实报价，不要断言这条航线没有航班。"
            f"{context}"
        )
