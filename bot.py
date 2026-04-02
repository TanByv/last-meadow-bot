from __future__ import annotations

import asyncio
import random
from collections import deque
from datetime import datetime, timezone, timedelta
from typing import Optional

from rich.live import Live

from client import GameClient
from display import make_dashboard
from models import ErrorResponse, GameResponse, UserData

# ── Timing constants ──────────────────────────────────────────────────────────

CRAFTING_COOLDOWN = timedelta(minutes=2)
COMBAT_COOLDOWN = timedelta(minutes=3)

# Seconds to wait between start → complete for timed events
EVENT_COMPLETE_DELAY_MIN = 3.0
EVENT_COMPLETE_DELAY_MAX = 4.2

# Delay between the start and complete requests for gathering
GATHER_INNER_DELAY_MIN = 0.40
GATHER_INNER_DELAY_MAX = 0.75

# Extra pause after completing any full activity cycle
CYCLE_EXTRA_DELAY_MIN = 0.10
CYCLE_EXTRA_DELAY_MAX = 0.35

LOG_SIZE = 15


class Bot:
    def __init__(
        self,
        session_token: str,
        super_properties: str,
        user_agent: str,
        target_level: Optional[int],
    ) -> None:
        self.session_token = session_token
        self.super_properties = super_properties
        self.user_agent = user_agent
        self.target_level = min(target_level, 100) if target_level is not None else None

        # State synced from server
        self.user_data: Optional[UserData] = None
        self.crafting_cooldown_until: Optional[datetime] = None
        self.combat_cooldown_until: Optional[datetime] = None

        # Session metrics
        self.session_start: datetime = datetime.now(timezone.utc)
        self.session_gathering: int = 0
        self.session_crafting: int = 0
        self.session_combat: int = 0
        self.session_xp_start: Optional[int] = None

        # Display state
        self.activity_log: deque[str] = deque(maxlen=LOG_SIZE)
        self.current_action: str = "Starting up…"

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _log(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.activity_log.append(f"[dim]{ts}[/dim]  {msg}")

    def _crafting_ready(self) -> bool:
        if self.crafting_cooldown_until is None:
            return True
        return datetime.now(timezone.utc) >= self.crafting_cooldown_until

    def _combat_ready(self) -> bool:
        if self.combat_cooldown_until is None:
            return True
        return datetime.now(timezone.utc) >= self.combat_cooldown_until

    def _ingest(self, resp: GameResponse) -> None:
        """Update local state from a successful server response."""
        self.user_data = resp.user_data
        if self.session_xp_start is None:
            self.session_xp_start = resp.user_data.xp

        ud = resp.user_data
        if ud.crafting_ended_at:
            self.crafting_cooldown_until = ud.crafting_ended_at + CRAFTING_COOLDOWN
        if ud.combat_ended_at:
            self.combat_cooldown_until = ud.combat_ended_at + COMBAT_COOLDOWN

    def _changes_str(self, resp: GameResponse) -> str:
        nz = resp.changes.nonzero()
        if not nz:
            return ""
        return "  " + "  ".join(f"[yellow]+{v} {k}[/yellow]" for k, v in nz.items())

    # ── Activity implementations ──────────────────────────────────────────────

    async def _do_gathering(self, client: GameClient, live: Live) -> None:
        self.current_action = "⛏  Gathering"
        live.update(make_dashboard(self))

        resp = await client.gathering_start()
        if not isinstance(resp, GameResponse):
            self._log("[red]✗ Gathering start failed[/red]")
            await asyncio.sleep(1.5)
            return
        self._ingest(resp)

        await asyncio.sleep(random.uniform(GATHER_INNER_DELAY_MIN, GATHER_INNER_DELAY_MAX))

        resp = await client.gathering_complete()
        if not isinstance(resp, GameResponse):
            self._log("[red]✗ Gathering complete failed[/red]")
            await asyncio.sleep(1.5)
            return
        self._ingest(resp)
        self.session_gathering += 1
        self._log(f"[green]✓ Gathering[/green]{self._changes_str(resp)}")

    async def _do_crafting(self, client: GameClient, live: Live) -> None:
        self.current_action = "🔨  Crafting (event)"
        live.update(make_dashboard(self))
        self._log("[cyan]→ Crafting event starting…[/cyan]")

        resp = await client.crafting_start()
        if isinstance(resp, ErrorResponse):
            self._log("[red]✗ Crafting still on cooldown (server-side)[/red]")
            # Be conservative — push our local estimate forward
            self.crafting_cooldown_until = datetime.now(timezone.utc) + CRAFTING_COOLDOWN
            return
        if not isinstance(resp, GameResponse):
            self._log("[red]✗ Crafting start failed[/red]")
            return
        self._ingest(resp)

        delay = random.uniform(EVENT_COMPLETE_DELAY_MIN, EVENT_COMPLETE_DELAY_MAX)
        self.current_action = f"🔨  Crafting… ({delay:.1f}s)"
        live.update(make_dashboard(self))
        await asyncio.sleep(delay)

        resp = await client.crafting_complete()
        if not isinstance(resp, GameResponse):
            self._log("[red]✗ Crafting complete failed[/red]")
            return
        self._ingest(resp)
        self.session_crafting += 1
        self._log(f"[cyan]✓ Crafting[/cyan]{self._changes_str(resp)}")

    async def _do_combat(self, client: GameClient, live: Live) -> None:
        self.current_action = "⚔  Combat (event)"
        live.update(make_dashboard(self))
        self._log("[magenta]→ Combat event starting…[/magenta]")

        resp = await client.combat_start()
        if isinstance(resp, ErrorResponse):
            self._log("[red]✗ Combat still on cooldown (server-side)[/red]")
            self.combat_cooldown_until = datetime.now(timezone.utc) + COMBAT_COOLDOWN
            return
        if not isinstance(resp, GameResponse):
            self._log("[red]✗ Combat start failed[/red]")
            return
        self._ingest(resp)

        delay = random.uniform(EVENT_COMPLETE_DELAY_MIN, EVENT_COMPLETE_DELAY_MAX)
        self.current_action = f"⚔  Combat… ({delay:.1f}s)"
        live.update(make_dashboard(self))
        await asyncio.sleep(delay)

        resp = await client.combat_complete()
        if not isinstance(resp, GameResponse):
            self._log("[red]✗ Combat complete failed[/red]")
            return
        self._ingest(resp)
        self.session_combat += 1
        self._log(f"[magenta]✓ Combat[/magenta]{self._changes_str(resp)}")

    # ── Main loop ─────────────────────────────────────────────────────────────

    async def run(self) -> None:
        async with GameClient(
            session_token=self.session_token,
            super_properties=self.super_properties,
            user_agent=self.user_agent,
        ) as client:
            with Live(
                make_dashboard(self),
                refresh_per_second=4,
                screen=True,
            ) as live:
                self._log("[bold green]Bot started[/bold green]")

                while True:
                    # ── Target level check ────────────────────────────────────
                    if (
                        self.target_level is not None
                        and self.user_data is not None
                        and self.user_data.level >= self.target_level
                    ):
                        self.current_action = f"🎉 Target level {self.target_level} reached!"
                        self._log(f"[bold green]🎉 Reached target level {self.target_level}! Stopping.[/bold green]")
                        live.update(make_dashboard(self))
                        await asyncio.sleep(3)
                        break

                    # ── Priority: combat ▸ crafting ▸ gathering ───────────────
                    if self._combat_ready():
                        await self._do_combat(client, live)
                    elif self._crafting_ready():
                        await self._do_crafting(client, live)
                    else:
                        await self._do_gathering(client, live)

                    live.update(make_dashboard(self))

                    # Small breath between full cycles
                    await asyncio.sleep(random.uniform(CYCLE_EXTRA_DELAY_MIN, CYCLE_EXTRA_DELAY_MAX))
