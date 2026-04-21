# posthog-telegram

Streams PostHog events to Telegram in real-time. Polls every 30s, deduplicates, and sends one message per event.

## Setup

### 1. Create Telegram bot
1. Message [@BotFather](https://t.me/botfather) → `/newbot`
2. Copy the token → `TELEGRAM_BOT_TOKEN`
3. Message your bot, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates` to get your `chat_id`

### 2. Get PostHog API key
PostHog → Settings → Personal API Keys → Create key with **Read** access

### 3. Get your Project ID
PostHog → Settings → Project → copy the numeric ID from the URL or settings page

### 4. Deploy to OCI

```bash
# Copy files
scp -r . ubuntu@server.jedbillyb.com:/opt/posthog-telegram

# SSH in
ssh ubuntu@server.jedbillyb.com

# Set up venv
cd /opt/posthog-telegram
python3 -m venv venv
venv/bin/pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env   # fill in your keys

# Install & start systemd service
sudo cp posthog-telegram.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now posthog-telegram

# Check it's running
sudo systemctl status posthog-telegram
sudo journalctl -u posthog-telegram -f
```

## Message format

Each event looks like:

```
📄 $pageview  14:32:01 UTC
  👤 abc12345…
  Current Url: https://vehiclefinder.co.nz/
  Browser: Chrome
  Os: Mac OS X
  Referring Domain: google.com
```

## Customise

- **Add event emojis**: edit `EVENT_EMOJI` dict in `bot.py`
- **Add vehiclefinder props**: already included (`query`, `make`, `model`, `year`)
- **Change poll rate**: set `POLL_INTERVAL` in `.env`
- **Filter events**: add an `if name not in IGNORE_EVENTS: continue` block in `main()`
