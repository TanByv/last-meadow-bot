from __future__ import annotations

import asyncio
import base64
import json
import sys

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from bot import Bot

console = Console()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _decode_super_properties(encoded: str) -> dict:
    """Decode a base64 x-super-properties string into a dict."""
    # Handle missing padding
    padded = encoded + "=" * (-len(encoded) % 4)
    try:
        raw = base64.b64decode(padded).decode("utf-8")
        return json.loads(raw)
    except Exception:
        return {}


# ── Interactive setup ─────────────────────────────────────────────────────────


def prompt_inputs() -> tuple[str, str, str, int | None]:
    """
    Walk the user through setup and return
    (session_token, super_properties, user_agent, target_level).
    """
    console.print()
    console.print(
        Panel.fit(
            Text.assemble(
                ("⚔  Last Meadow Online\n", "bold green"),
                ("   Automated Grinding Bot  v1.0", "dim"),
            ),
            border_style="green",
            padding=(0, 4),
        )
    )
    console.print()

    # ── Credentials ───────────────────────────────────────────────────────────
    session_token = Prompt.ask("[bold cyan]Session token[/bold cyan]")
    console.print()

    super_properties = Prompt.ask("[bold cyan]x-super-properties[/bold cyan] [dim](base64 string)[/dim]")
    console.print()

    # ── Parse super-properties ────────────────────────────────────────────────
    props = _decode_super_properties(super_properties)
    if props:
        browser = props.get("browser", "?")
        version = props.get("browser_version", "?")
        os_name = props.get("os", "?")
        user_agent = props.get(
            "browser_user_agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        )
        console.print(f"  [green]✓[/green] Detected client  : {browser} {version} on {os_name}")
        console.print(f"  [green]✓[/green] User-Agent       : [dim]{user_agent[:72]}…[/dim]")
    else:
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

    console.print()

    # ── Target level ──────────────────────────────────────────────────────────
    target_raw = Prompt.ask(
        "[bold cyan]Target level[/bold cyan] [dim](1-100 or 'inf')[/dim]",
        default="inf",
    )
    target_level: int | None
    if target_raw.strip().lower() in ("inf", "infinite", ""):
        target_level = None
        console.print("  [green]✓[/green] Running indefinitely.")
    else:
        try:
            target_level = int(target_raw)
            if target_level > 100:
                console.print(f"  [yellow]⚠ Level {target_level} exceeds game limit. Clamping to [bold]100[/bold].[/yellow]")
                target_level = 100
            console.print(f"  [green]✓[/green] Will stop at level [bold yellow]{target_level}[/bold yellow].")
        except ValueError:
            console.print("  [yellow]⚠ Invalid number — running indefinitely.[/yellow]")
            target_level = None

    console.print()
    return session_token, super_properties, user_agent, target_level


# ── Entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    try:
        session_token, super_properties, user_agent, target_level = prompt_inputs()

        console.print("[bold green]Launching bot…[/bold green]\n")

        bot = Bot(
            session_token=session_token,
            super_properties=super_properties,
            user_agent=user_agent,
            target_level=target_level,
        )

        asyncio.run(bot.run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped by user (Ctrl+C).[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    main()
