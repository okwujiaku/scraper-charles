# Charles Discord Join Scraper (Option C — one worker per brand)

Self-bot join tracker for **charlesmark333** — forwards captures to the
**Charles Auto wise** group chat. Uses the simple, proven pikanto model:
one `on_message` handler watches the log-bot's **New Member Joined!** posts and
forwards a **NEW MEMBER CAPTURED** card to one group chat. No gateway-event
guessing, no startup grace — just the flow that works.

## Folder layout

```
scraper-charles/
├── bot/
│   ├── bot.py            # the actual bot (run this)
│   ├── requirements.txt
│   └── .env.example
├── scripts/new-customer.sh
├── templates/render-env.example
├── bot.py                # launcher (runs bot/bot.py from repo root)
├── requirements.txt      # -r bot/requirements.txt
├── .env                  # USER_TOKEN + CHAT_ID (never commit)
├── .gitignore
└── README.md
```

## How it captures

charlesmark333 is its own "Smart Tech" + forwarder. It detects new joins three
ways and forwards a `NEW MEMBER CAPTURED` card to the group chat:

1. **Gateway joins** — on startup it calls `guild.subscribe(member_updates=True)`
   on every server (requires `discord.py-self>=2.1`), so `on_member_join` fires
   for live joins. Reports joins newer than `JOIN_MAX_AGE_SECONDS` (default 600s).
2. **Join system messages** — Discord's native "X joined" messages in a welcome
   channel the account can read.
3. **Log-bot / welcome-bot posts** — "New Member Joined!" cards or "Welcome @user"
   greetings.

Coverage still depends on the account being a member of the servers and able to
read the relevant channels. Very large servers (>75k members) and servers that
hide join activity may yield fewer or no events — that's a Discord limitation for
user accounts, not a bug.

## Local run

```powershell
cd C:\Users\HP\Downloads\scraper-charles
pip install -r requirements.txt
python bot.py
```

`bot.py` (root) is a launcher that runs `bot/bot.py`. It loads `.env` from the
repo root (or `bot/.env` if present). Run **one** instance per token.

## Render (Background Worker)

- **Root Directory:** `bot` (recommended) or repo root (`bot.py` launcher)
- **Build:** `pip install -r requirements.txt`
- **Start:** `python bot.py`
- **Env:** `DISCORD_TOKEN` (user token) + `CHAT_ID` + `CLIENT_NAME=Charles` + `PYTHON_VERSION=3.11.9`

Render never reads your local `.env`; set every variable in the dashboard.

Self-botting violates Discord ToS; use at your own risk.
