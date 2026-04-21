<div align="center">

# posthog-telegram

**Streams PostHog events to Telegram in real-time.**

[![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=flat-square&logo=python)](https://www.python.org)
[![PostHog](https://img.shields.io/badge/PostHog-Events-f54e00?style=flat-square)](https://posthog.com)

</div>

---

Polls the PostHog Events API every 30 seconds, deduplicates results, and fires one Telegram message per event. Designed to run as a systemd service on a VPS.

## Features

- **Real-time alerts** — New events land in Telegram within 30 seconds
- **Deduplication** — Seen event IDs are cached so nothing fires twice
- **Rich formatting** — Emojis, timestamps, user IDs, and key properties per event
- **vehiclefinder-aware** — Ships with `query`, `make`, `model`, and `year` prop support out of the box
- **Configurable** — Poll interval, ignored events, and emoji map all controlled via `.env` or `bot.py`

## Stack

| Layer | Tech |
|---|---|
| Language | Python 3.10+ |
| APIs | PostHog Events API, Telegram Bot API |
| Process management | systemd |
| Config | `.env` via `python-dotenv` |

## Getting Started

```bash
git clone https://github.com/jedbillyb/posthog-telegram.git
cd posthog-telegram
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:

```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
POSTHOG_API_KEY=...
POSTHOG_PROJECT_ID=...
POLL_INTERVAL=30
```

**Getting your Telegram chat ID:** message your bot, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates`.

Run locally:

```bash
venv/bin/python bot.py
```

## Deployment

Copy to your VPS and install the systemd service:

```bash
scp -r . ubuntu@server.jedbillyb.com:/opt/posthog-telegram
ssh ubuntu@server.jedbillyb.com

cd /opt/posthog-telegram
python3 -m venv venv
venv/bin/pip install -r requirements.txt
nano .env  # fill in your keys

sudo cp posthog-telegram.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now posthog-telegram
sudo journalctl -u posthog-telegram -f
```

## Message Format

```
📄 $pageview  14:32:01 UTC
  👤 abc12345…
  Current Url: https://vehiclefinder.co.nz/
  Browser: Chrome
  Os: Mac OS X
  Referring Domain: google.com
```

---

<div align="center">
<sub>MIT © <a href="https://github.com/jedbillyb">jedbillyb</a> · Made with ❤️</sub>
</div>
