# Last Meadow Online — Grinding Bot

Automates the Last Meadow Online game loop:

- **Prioritises** Crafting (2 min cooldown) and Combat (3 min cooldown) events
- **Fills downtime** with continuous Gathering cycles (~1/second)
- **Live dashboard** showing cooldowns, stats, XP, and activity log
- **Stops automatically** when target level is reached (or runs forever)

---

## Requirements

Python 3.11+

```bash
pip install -r requirements.txt
```

---

## Usage

```bash
python main.py
```

You will be prompted for:

> [!IMPORTANT]
> **DISCLAIMER**: Use this bot at your own risk. The developers are not responsible for any bans or account actions. This tool is for educational purposes only.
> **Note**: The maximum possible level is **100**.

| Input | Description |
|---|---|
| **Session token** | Your `authorization` header value |
| **x-super-properties** | Base64 string from the request headers |
| **Target level** | A number like `50`, or `inf` to run forever |

---

## Project structure

```
last_meadow_bot/
├── main.py          # Entry point & interactive CLI
├── bot.py           # Game loop, activity logic, timing
├── client.py        # curl_cffi async HTTP client
├── display.py       # Rich live dashboard renderer
├── models.py        # Pydantic response models
└── requirements.txt
```

---

## Timing at a glance

| Activity | Start → Complete delay | Cooldown |
|---|---|---|
| Gathering | 0.4 – 0.75 s | none |
| Crafting | 3.0 – 4.2 s | 2 minutes |
| Combat | 3.0 – 4.2 s | 3 minutes |

A small extra jitter (0.1 – 0.35 s) is added between every full cycle.