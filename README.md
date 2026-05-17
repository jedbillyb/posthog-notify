<p align="right"><a href="https://jedbillyb.com"><img src="https://img.shields.io/badge/jedbillyb.com-000?style=for-the-badge&logo=archlinux&logoColor=blue" /></a></p>
<div align="center">

# posthog-telegram

**Forwards PostHog webhook events to Telegram in real-time.**

[![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=flat-square&logo=python)](https://www.python.org)
[![PostHog](https://img.shields.io/badge/PostHog-Webhooks-f54e00?style=flat-square)](https://posthog.com)

</div>

---

A lightweight FastAPI webhook receiver. PostHog pushes events to `/posthog`, the service filters noise, extracts key properties, and fires a formatted message to Telegram. Designed to run as a systemd service on a VPS.

## Features

- **Webhook-driven** — Zero polling; PostHog pushes events instantly
- **Noise filtering** — Configurable `SKIP_EVENTS` set drops web vitals, autocapture, and other noise
- **Rich formatting** — Site label, event name, timestamp, location, URL, and device info per message
- **vehiclefinder-aware** — Extracts `make`, `model`, and `year` for vehicle search events
- **Fuzzy property matching** — Handles inconsistent PostHog key casing and formatting automatically

## Stack

| Layer | Tech |
|---|---|
| Language | Python 3.10+ |
| Web framework | FastAPI |
| HTTP client | requests |
| APIs | PostHog Webhooks, Telegram Bot API |
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
```

**Getting your Telegram chat ID:** message your bot, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates`.

Run locally:

```bash
venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```

### PostHog setup

In PostHog → **Project Settings** → **Webhooks**, add your endpoint:

```
https://your-domain.com/posthog
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

The service must be reachable from the internet — proxy it through nginx or Caddy on your VPS.

## Message Format

```
VF · Pageview  14:32:01 UTC
abc12345…  ·  Auckland, New Zealand
/stats/toyota?make=toyota
Chrome  ·  Mac OS X
```

For vehicle search events, a vehicle line is prepended:

```
VF · Pageview  14:32:01 UTC
2018 Toyota Corolla
abc12345…  ·  Wellington, New Zealand
/search
Chrome  ·  Windows
```

---

<div align="center">
<sub>MIT © <a href="https://github.com/jedbillyb">jedbillyb</a> · Made with ❤️</sub>
</div>
