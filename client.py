from __future__ import annotations

from typing import Union

from curl_cffi.requests import AsyncSession

from models import ErrorResponse, GameResponse

BASE_URL = "https://discord.com/api/v9/gorilla"


class GameClient:
    def __init__(
        self,
        session_token: str,
        super_properties: str,
        user_agent: str,
    ) -> None:
        self._session_token = session_token
        self._super_properties = super_properties
        self._user_agent = user_agent
        self._session: AsyncSession | None = None

    # ── Session lifecycle ────────────────────────────────────────────────────

    async def __aenter__(self) -> GameClient:
        self._session = AsyncSession(impersonate="chrome")
        return self

    async def __aexit__(self, *_) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    # ── Shared helpers ───────────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        return {
            "accept": "*/*",
            "accept-language": "en-US",
            "authorization": self._session_token,
            "content-length": "0",
            "origin": "https://discord.com",
            "priority": "u=1, i",
            "user-agent": self._user_agent,
            "x-super-properties": self._super_properties,
        }

    async def _post(self, path: str) -> Union[GameResponse, ErrorResponse, None]:
        assert self._session, "Client not entered via async context manager"
        try:
            resp = await self._session.post(
                f"{BASE_URL}{path}",
                headers=self._headers(),
                data=b"",
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception:
            # Re-try once on connection-level failures
            try:
                resp = await self._session.post(
                    f"{BASE_URL}{path}",
                    headers=self._headers(),
                    data=b"",
                )
                payload = resp.json()
            except Exception:
                return None

        if "message" in payload and "code" in payload:
            return ErrorResponse(**payload)
        try:
            return GameResponse(**payload)
        except Exception:
            return None

    # ── Gathering ────────────────────────────────────────────────────────────

    async def gathering_start(self) -> Union[GameResponse, ErrorResponse, None]:
        return await self._post("/activity/gathering/start")

    async def gathering_complete(self) -> Union[GameResponse, ErrorResponse, None]:
        return await self._post("/activity/gathering/complete")

    # ── Crafting (1st event, 2-min cooldown) ─────────────────────────────────

    async def crafting_start(self) -> Union[GameResponse, ErrorResponse, None]:
        return await self._post("/activity/crafting/start")

    async def crafting_complete(self) -> Union[GameResponse, ErrorResponse, None]:
        return await self._post("/activity/crafting/complete")

    # ── Combat (2nd event, 3-min cooldown) ───────────────────────────────────

    async def combat_start(self) -> Union[GameResponse, ErrorResponse, None]:
        return await self._post("/activity/combat/start")

    async def combat_complete(self) -> Union[GameResponse, ErrorResponse, None]:
        return await self._post("/activity/combat/complete")
