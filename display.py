from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from rich import box
from rich.columns import Columns
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from bot import Bot


# ── Helpers ──────────────────────────────────────────────────────────────────


def _fmt_cd(cooldown_until: Optional[datetime], now: datetime) -> str:
    """Return a coloured cooldown string."""
    if cooldown_until is None:
        return "[bold green]  READY  [/bold green]"
    remaining = (cooldown_until - now).total_seconds()
    if remaining <= 0:
        return "[bold green]  READY  [/bold green]"
    m, s = divmod(int(remaining), 60)
    return f"[yellow]  {m:01d}:{s:02d}  [/yellow]"


def _fmt_ready_at(cooldown_until: Optional[datetime], now: datetime) -> str:
    if cooldown_until is None:
        return ""
    if now >= cooldown_until:
        return ""
    return f"[dim]ready @ {cooldown_until.astimezone().strftime('%H:%M:%S')}[/dim]"


def _elapsed(start: datetime, now: datetime) -> str:
    s = int((now - start).total_seconds())
    h, remainder = divmod(s, 3600)
    m, sec = divmod(remainder, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"


def _level_bar(level: int, width: int = 10) -> str:
    """Decorative bar cycling every 10 levels."""
    filled = level % 10 or 10
    return f"[cyan]{'█' * filled}{'░' * (width - filled)}[/cyan]"


# ── Main dashboard ────────────────────────────────────────────────────────────


def make_dashboard(bot: "Bot") -> Group:
    ud = bot.user_data
    now = datetime.now(timezone.utc)

    # ── Top status bar ────────────────────────────────────────────────────────
    target_str = f"Lv {bot.target_level}" if bot.target_level else "∞"
    status_bar = Text.assemble(
        ("⚔  Last Meadow Online Bot", "bold green"),
        ("   │   ", "dim"),
        ("Uptime: ", "dim"),
        (_elapsed(bot.session_start, now), "bold cyan"),
        ("   │   ", "dim"),
        ("Target: ", "dim"),
        (target_str, "bold yellow"),
        ("   │   ", "dim"),
        (bot.current_action, "bold white"),
    )
    header = Panel(status_bar, box=box.HEAVY, border_style="green", padding=(0, 1))

    # ── Character panel ───────────────────────────────────────────────────────
    char_tbl = Table(box=None, show_header=False, padding=(0, 2))
    char_tbl.add_column(style="dim", min_width=14)
    char_tbl.add_column(style="bold white", min_width=26)

    if ud:
        xp_gained = (ud.xp - bot.session_xp_start) if bot.session_xp_start is not None else 0
        char_tbl.add_row("Level", f"{ud.level}  {_level_bar(ud.level)}")
        char_tbl.add_row("XP", f"{ud.xp:,}   [green](+{xp_gained:,} session)[/green]")
        char_tbl.add_row("Crafting class", ud.crafting_class.replace("_", " ").title())
        char_tbl.add_row("Combat class", ud.combat_class.replace("_", " ").title())
        char_tbl.add_row("User ID", f"[dim]{ud.user_id}[/dim]")
    else:
        char_tbl.add_row("Status", "[yellow]Awaiting first response…[/yellow]")

    char_panel = Panel(
        char_tbl,
        title="[bold blue]Character[/bold blue]",
        border_style="blue",
        box=box.ROUNDED,
        padding=(0, 1),
    )

    # ── Cooldowns panel ───────────────────────────────────────────────────────
    cd_tbl = Table(box=None, show_header=False, padding=(0, 2))
    cd_tbl.add_column(style="dim", min_width=18)
    cd_tbl.add_column(min_width=12)
    cd_tbl.add_column(min_width=20)

    cd_tbl.add_row(
        "Crafting  [dim](2 min)[/dim]",
        _fmt_cd(bot.crafting_cooldown_until, now),
        _fmt_ready_at(bot.crafting_cooldown_until, now),
    )
    cd_tbl.add_row(
        "Combat  [dim](3 min)[/dim]",
        _fmt_cd(bot.combat_cooldown_until, now),
        _fmt_ready_at(bot.combat_cooldown_until, now),
    )

    cd_panel = Panel(
        cd_tbl,
        title="[bold yellow]Cooldowns[/bold yellow]",
        border_style="yellow",
        box=box.ROUNDED,
        padding=(0, 1),
    )

    # ── Session counters panel ────────────────────────────────────────────────
    sess_tbl = Table(box=None, show_header=False, padding=(0, 2))
    sess_tbl.add_column(style="dim", min_width=10)
    sess_tbl.add_column(style="bold", min_width=8)

    total = bot.session_gathering + bot.session_crafting + bot.session_combat
    sess_tbl.add_row("Gathering", f"[green]{bot.session_gathering:,}[/green]")
    sess_tbl.add_row("Crafting", f"[cyan]{bot.session_crafting:,}[/cyan]")
    sess_tbl.add_row("Combat", f"[magenta]{bot.session_combat:,}[/magenta]")
    sess_tbl.add_row("Total", f"[bold white]{total:,}[/bold white]")

    sess_panel = Panel(
        sess_tbl,
        title="[bold green]Session[/bold green]",
        border_style="green",
        box=box.ROUNDED,
        padding=(0, 1),
    )

    # ── All-time stats panel ──────────────────────────────────────────────────
    stats_tbl = Table(box=None, show_header=False, padding=(0, 2))
    stats_tbl.add_column(style="dim", min_width=10)
    stats_tbl.add_column(style="bold white", min_width=8)

    if ud:
        ac = ud.stats.activity_completion
        rc = ud.stats.resource_contribution
        stats_tbl.add_row("[green]Gathering[/green]", str(ac.gathering))
        stats_tbl.add_row("[cyan]Crafting[/cyan]", str(ac.crafting))
        stats_tbl.add_row("[magenta]Combat[/magenta]", str(ac.combat))
        stats_tbl.add_row("", "")
        stats_tbl.add_row("[dim]Metal[/dim]", str(rc.metal))
        stats_tbl.add_row("[dim]Wood[/dim]", str(rc.wood))
        stats_tbl.add_row("[dim]Leather[/dim]", str(rc.leather))
        stats_tbl.add_row("[dim]Weapon[/dim]", str(rc.weapon))
        stats_tbl.add_row("[dim]Healers[/dim]", str(rc.healers))
    else:
        stats_tbl.add_row("Status", "[yellow]Loading…[/yellow]")

    stats_panel = Panel(
        stats_tbl,
        title="[bold magenta]All-Time Stats[/bold magenta]",
        border_style="magenta",
        box=box.ROUNDED,
        padding=(0, 1),
    )

    # ── Activity log ──────────────────────────────────────────────────────────
    log_lines = list(bot.activity_log)
    log_text = "\n".join(log_lines) if log_lines else "[dim]No activity yet…[/dim]"
    log_panel = Panel(
        log_text,
        title="[bold]Activity Log[/bold]",
        border_style="dim",
        box=box.ROUNDED,
        padding=(0, 1),
    )

    return Group(
        header,
        Columns([char_panel, cd_panel], equal=True, expand=True),
        Columns([sess_panel, stats_panel], equal=True, expand=True),
        log_panel,
    )
