import asyncio
import aiohttp
import ssl
import certifi
from typing import Dict, Any, Optional
from config.settings import config

class HideMyEmail:
    def __init__(self, cookies: str = ""):
        self.base_url_v1 = config.get("DEFAULT", "base_url_v1")
        self.base_url_v2 = config.get("DEFAULT", "base_url_v2")
        self.params = config.params
        self.label = config.get("DEFAULT", "label")
        self.cookies = cookies

    async def __aenter__(self):
        connector = aiohttp.TCPConnector(
            ssl_context=ssl.create_default_context(cafile=certifi.where())
        )
        self.session = aiohttp.ClientSession(
            headers=self._get_headers(),
            timeout=aiohttp.ClientTimeout(total=10),
            connector=connector,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Connection": "keep-alive",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Content-Type": "text/plain",
            "Accept": "*/*",
            "Sec-GPC": "1",
            "Origin": "https://www.icloud.com",
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Referer": "https://www.icloud.com/",
            "Accept-Language": "en-US,en-GB;q=0.9,en;q=0.8,cs;q=0.7",
            "Cookie": self.cookies.strip(),
        }

    @property
    def cookies(self) -> str:
        return self._cookies

    @cookies.setter
    def cookies(self, cookies: str):
        self._cookies = cookies.strip()

    async def generate_email(self) -> Dict[str, Any]:
        try:
            async with self.session.post(
                f"{self.base_url_v1}/generate",
                params=self.params,
                json={"langCode": "en-us"}
            ) as resp:
                return await resp.json()
        except asyncio.TimeoutError:
            return {"error": 1, "reason": "So'rov vaqti tugadi"}
        except Exception as e:
            return {"error": 1, "reason": str(e)}

    async def reserve_email(self, email: str) -> Dict[str, Any]:
        try:
            payload = {
                "hme": email,
                "label": self.label,
                "note": "rtuna's iCloud email generator tomonidan yaratilgan",
            }
            async with self.session.post(
                f"{self.base_url_v1}/reserve",
                params=self.params,
                json=payload
            ) as resp:
                return await resp.json()
        except asyncio.TimeoutError:
            return {"error": 1, "reason": "So'rov vaqti tugadi"}
        except Exception as e:
            return {"error": 1, "reason": str(e)}

    async def list_email(self) -> Dict[str, Any]:
        try:
            async with self.session.get(
                f"{self.base_url_v2}/list",
                params=self.params
            ) as resp:
                return await resp.json()
        except asyncio.TimeoutError:
            return {"error": 1, "reason": "So'rov vaqti tugadi"}
        except Exception as e:
            return {"error": 1, "reason": str(e)}
