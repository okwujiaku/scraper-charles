"""
Charles join tracker — log-bot parser only (self-bot).

Watches log-bot "New Member Joined!" messages (on_message) and forwards a
capture card to one group chat. Same strict model as Documents/scraper (Pikanto).

Set USER_TOKEN + CHAT_ID in .env or on Render.

WARNING: Automating a user account (self-botting) violates Discord's ToS.
"""

import asyncio
import os
import re
import sys
import time

import discord
from dotenv import load_dotenv

USER_TOKEN = ""

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

try:
    import colorama
    colorama.just_fix_windows_console()
except Exception:
    pass

try:
    _orig_parse_ready_supplemental = (
        discord.state.ConnectionState.parse_ready_supplemental
    )

    def _safe_parse_ready_supplemental(self, extra_data, *args, **kwargs):
        ready = getattr(self, "_ready_data", None)
        if isinstance(ready, dict) and ready.get("pending_payments") is None:
            ready["pending_payments"] = []
        return _orig_parse_ready_supplemental(self, extra_data, *args, **kwargs)

    discord.state.ConnectionState.parse_ready_supplemental = (
        _safe_parse_ready_supplemental
    )
except Exception:
    pass

_FALLBACK_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
)
try:
    from discord import utils as _discord_utils

    _orig_get_user_agent = _discord_utils._get_user_agent

    async def _get_user_agent_safe(session):
        try:
            return await _orig_get_user_agent(session)
        except Exception:
            print(
                f"[Charles] User-agent fetch failed (network/DNS); using fallback.",
                flush=True,
            )
            return _FALLBACK_USER_AGENT

    _discord_utils._get_user_agent = _get_user_agent_safe

    _orig_get_build_number = _discord_utils._get_build_number

    async def _get_build_number_safe(session):
        try:
            return await _orig_get_build_number(session)
        except Exception:
            print(
                f"[Charles] Build number fetch failed (network/DNS); using fallback.",
                flush=True,
            )
            return 9999

    _discord_utils._get_build_number = _get_build_number_safe
except Exception:
    pass


class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GOLD = "\033[38;5;220m"
    CYAN = "\033[38;5;51m"
    GREEN = "\033[38;5;48m"
    PINK = "\033[38;5;213m"
    PURPLE = "\033[38;5;141m"
    GRAY = "\033[38;5;245m"
    WHITE = "\033[97m"


_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.isfile(_env_path):
    load_dotenv(_env_path)

_env_token = (
    os.getenv("USER_TOKEN")
    or os.getenv("DISCORD_TOKEN")
    or os.getenv("TOKEN")
    or ""
).strip()
if _env_token:
    USER_TOKEN = _env_token

CLIENT_NAME = (os.getenv("CLIENT_NAME") or "Charles").strip()
CHAT_ID = (
    os.getenv("CHAT_ID")
    or os.getenv("FORWARD_CHAT_ID")
    or ""
).strip()
SEND_STARTUP_PING = (os.getenv("SEND_STARTUP_PING") or "true").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)

FIELD_STYLE = [
    ("Date", "date", "📅", C.CYAN),
    ("Time", "time", "⏰", C.CYAN),
    ("Username", "username", "👤", C.GREEN),
    ("User ID", "user_id", "🆔", C.PURPLE),
    ("Target Server", "server_name", "🏠", C.PURPLE),
]

CAPTURE_TITLE = "✨ NEW MEMBER CAPTURED ✨"


def process_extracted_data(data: dict) -> None:
    rows = [
        (label, icon, color, data.get(key) or "N/A")
        for label, key, icon, color in FIELD_STYLE
    ]

    title = CAPTURE_TITLE
    title_cells = len(title) + 2
    label_width = max(len(label) for label, *_ in rows)
    inner_width = max(
        title_cells,
        max(3 + label_width + 3 + len(str(value)) for *_, value in rows),
    )

    top = f"{C.GOLD}╔{'═' * (inner_width + 2)}╗{C.RESET}"
    sep = f"{C.GOLD}╠{'═' * (inner_width + 2)}╣{C.RESET}"
    bot_line = f"{C.GOLD}╚{'═' * (inner_width + 2)}╝{C.RESET}"
    bar = f"{C.GOLD}║{C.RESET}"
    title_pad = inner_width - title_cells
    left = title_pad // 2
    right = title_pad - left

    print()
    print(f"[{CLIENT_NAME}] capture detected", flush=True)
    print(top)
    print(f"{bar} {' ' * left}{C.BOLD}{C.PINK}{title}{C.RESET}{' ' * right} {bar}")
    print(sep)
    for label, icon, color, value in rows:
        plain_len = 3 + label_width + 3 + len(str(value))
        pad = " " * (inner_width - plain_len)
        print(
            f"{bar} {icon} {color}{label:<{label_width}}{C.RESET}"
            f"{C.GRAY} : {C.RESET}{C.WHITE}{value}{C.RESET}{pad} {bar}"
        )
    print(bot_line)
    print()


def format_capture_message(data: dict) -> str:
    """Plain text for group DM — self-bots cannot use embeds."""
    lines = [f"**{CAPTURE_TITLE}**"]
    for label, key, icon, _ in FIELD_STYLE:
        value = str(data.get(key) or "N/A")
        if key == "username":
            value = f"`{value}`"
        lines.append(f"{icon} **{label}:** {value}")
    lines.extend(["", "─" * 28])
    return "\n".join(lines)


def collect_message_text(message: discord.Message) -> str:
    parts = [message.content or ""]
    for embed in message.embeds:
        parts.append(embed.title or "")
        parts.append(embed.description or "")
        if embed.author:
            parts.append(embed.author.name or "")
        if embed.footer:
            parts.append(embed.footer.text or "")
        for field in embed.fields:
            name = (field.name or "").strip()
            value = (field.value or "").strip()
            if name and value:
                parts.append(f"{name}: {value}")
            else:
                parts.append(name)
                parts.append(value)
    return "\n".join(parts)


def is_join_log(text: str) -> bool:
    lowered = text.lower()
    return (
        "username:" in lowered
        and "user id:" in lowered
        and ("new member joined" in lowered or "member joined!" in lowered)
    )


def parse_join_log(full_text: str) -> dict | None:
    if not is_join_log(full_text):
        return None

    def clean(match):
        if not match:
            return None
        return match.group(1).strip().replace("**", "").replace("`", "").strip()

    server = clean(
        re.search(r"Target\s+Server:\s*(.+)", full_text, re.IGNORECASE)
    ) or clean(re.search(r"Server:\s*(.+)", full_text, re.IGNORECASE))

    return {
        "date": clean(re.search(r"Date:\s*(.+)", full_text, re.IGNORECASE)),
        "time": clean(re.search(r"Time:\s*(.+)", full_text, re.IGNORECASE)),
        "username": clean(re.search(r"Username:\s*(.+)", full_text, re.IGNORECASE)),
        "server_name": server,
        "user_id": clean(re.search(r"User ID:\s*(.+)", full_text, re.IGNORECASE)),
    }


class ScraperClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._recent_captures: dict[tuple[str, str], float] = {}
        self._forward_channel: discord.abc.Messageable | None = None
        self._ready_once = False
        self._capture_lock = asyncio.Lock()

    async def _open_forward_channel(self) -> None:
        self._forward_channel = None
        if not CHAT_ID:
            print(
                f"[{CLIENT_NAME}] No CHAT_ID set — terminal only.",
                flush=True,
            )
            return
        try:
            channel_id = int(CHAT_ID)
        except ValueError:
            print(f"[{CLIENT_NAME}] Invalid CHAT_ID: {CHAT_ID!r}", flush=True)
            return
        try:
            channel = self.get_channel(channel_id)
            if channel is None:
                channel = await self.fetch_channel(channel_id)
            self._forward_channel = channel
            label = getattr(channel, "name", None) or str(channel)
            print(
                f"[{CLIENT_NAME}] Forwarding captures to: {label} (id: {channel_id})",
                flush=True,
            )
        except Exception as exc:
            print(
                f"[{CLIENT_NAME}] Could not open chat {CHAT_ID}: {exc}",
                flush=True,
            )

    async def _send_to_group(self, content: str) -> bool:
        if not self._forward_channel:
            return False
        try:
            await self._forward_channel.send(content)
            return True
        except Exception as exc:
            print(f"[{CLIENT_NAME}] Forward failed: {exc}", flush=True)
            return False

    async def _emit_capture(self, data: dict) -> None:
        user_id = str(data.get("user_id") or "")
        server = str(data.get("server_name") or "N/A").strip()
        key = (user_id, server.lower())
        now = time.time()

        async with self._capture_lock:
            if user_id and key in self._recent_captures:
                if now - self._recent_captures[key] < 90:
                    return
            if user_id:
                self._recent_captures[key] = now

        process_extracted_data(data)
        if await self._send_to_group(format_capture_message(data)):
            username = data.get("username") or "unknown"
            print(
                f"[{CLIENT_NAME}] Forwarded capture for {username}.",
                flush=True,
            )

    async def _send_startup_ping(self) -> None:
        if not SEND_STARTUP_PING or not self._forward_channel:
            return
        n = len(self.guilds)
        text = (
            f"🟢 **{CLIENT_NAME}** online — watching **{n}** server(s) "
            "for log-bot join messages."
        )
        if await self._send_to_group(text):
            print(f"[{CLIENT_NAME}] Startup ping sent to group chat.", flush=True)

    async def on_disconnect(self):
        print(
            f"[{CLIENT_NAME}] Disconnected — check Wi‑Fi/VPN/DNS. Reconnecting...",
            flush=True,
        )

    async def on_resumed(self):
        print(f"[{CLIENT_NAME}] Connection resumed.", flush=True)

    async def on_ready(self):
        print(f"[{CLIENT_NAME}] Logged in as {self.user} (id: {self.user.id})", flush=True)
        await self._open_forward_channel()
        print(
            f"[{CLIENT_NAME}] Watching {len(self.guilds)} server(s) for log-bot join messages...",
            flush=True,
        )
        guild_names = sorted(g.name for g in self.guilds)
        preview = ", ".join(guild_names[:10])
        if len(guild_names) > 10:
            preview += f", ... (+{len(guild_names) - 10} more)"
        print(f"[{CLIENT_NAME}] Servers: {preview}", flush=True)

        if self._ready_once:
            return
        self._ready_once = True

        await self._send_startup_ping()
        print(
            f"[{CLIENT_NAME}] Waiting for log-bot posts with "
            "Username:, User ID:, and New Member Joined!.\n",
            flush=True,
        )

    async def on_message(self, message):
        if message.author.id == self.user.id:
            return

        data = parse_join_log(collect_message_text(message))
        if data is None:
            return

        await self._emit_capture(data)


def _is_network_error(exc: BaseException) -> bool:
    name = type(exc).__name__
    text = str(exc).lower()
    return (
        "gaierror" in name.lower()
        or "ClientConnectorDNSError" in name
        or "getaddrinfo" in text
        or "cannot connect to host" in text
    )


async def main():
    if not USER_TOKEN:
        raise SystemExit(
            "No token set. Set USER_TOKEN in .env or on Render."
        )

    print(f"[{CLIENT_NAME}] Starting scraper...", flush=True)
    client = ScraperClient()

    for attempt in range(1, 6):
        try:
            await client.start(USER_TOKEN)
            return
        except KeyboardInterrupt:
            print(f"\n[{CLIENT_NAME}] Stopped.", flush=True)
            return
        except Exception as exc:
            if _is_network_error(exc) and attempt < 5:
                wait = 15 * attempt
                print(
                    f"[{CLIENT_NAME}] Network/DNS error (attempt {attempt}/5). "
                    f"Retrying in {wait}s...",
                    flush=True,
                )
                await asyncio.sleep(wait)
                continue
            raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Charles] Stopped.", flush=True)
