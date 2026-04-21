#!/usr/bin/env python3
"""
PostHog → Telegram Bot
Polls PostHog Cloud for new events and forwards them to Telegram in real-time.
"""

import os
import json
import time
import logging
import requests
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────

POSTHOG_API_KEY     = os.environ["POSTHOG_API_KEY"]       # Personal API key
POSTHOG_PROJECT_ID  = os.environ["POSTHOG_PROJECT_ID"]    # Numeric project ID
POSTHOG_HOST        = os.environ.get("POSTHOG_HOST", "https://app.posthog.com")

TELEGRAM_BOT_TOKEN  = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID    = os.environ["TELEGRAM_CHAT_ID"]

POLL_INTERVAL       = int(os.environ.get("POLL_INTERVAL", "30"))   # seconds
BATCH_SIZE          = int(os.environ.get("BATCH_SIZE", "50"))       # events per poll
STATE_FILE          = Path(os.environ.get("STATE_FILE", "/tmp/posthog_bot_state.json"))

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Event emoji map ───────────────────────────────────────────────────────────

EVENT_EMOJI = {
    "$pageview":          "📄",
    "$pageleave":         "🚪",
    "$autocapture":       "🖱️",
    "$identify":          "👤",
    "$set":               "⚙️",
    "$groupidentify":     "👥",
    "click":              "🖱️",
    "search":             "🔍",
    "error":              "🚨",
    "sponsor":            "💛",
    "submit":             "📨",
}

def event_emoji(name: str) -> str:
    for key, emoji in EVENT_EMOJI.items():
        if key in name.lower():
            return emoji
    return "⚡"

# ── State persistence ─────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {"last_timestamp": None, "seen_ids": []}

def save_state(state: dict):
    # Keep seen_ids capped to avoid unbounded growth
    state["seen_ids"] = state["seen_ids"][-500:]
    STATE_FILE.write_text(json.dumps(state))

# ── PostHog API ───────────────────────────────────────────────────────────────

def fetch_events(after: str | None) -> list[dict]:
    url = f"{POSTHOG_HOST}/api/projects/{POSTHOG_PROJECT_ID}/events/"
    params = {
        "orderBy": "-timestamp",
        "limit": BATCH_SIZE,
    }
    if after:
        params["after"] = after

    resp = requests.get(
        url,
        headers={"Authorization": f"Bearer {POSTHOG_API_KEY}"},
        params=params,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("results", [])

# ── Telegram API ──────────────────────────────────────────────────────────────

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    resp = requests.post(url, json=payload, timeout=10)
    if not resp.ok:
        log.warning("Telegram error %s: %s", resp.status_code, resp.text[:200])

# ── Event formatting ──────────────────────────────────────────────────────────

def format_event(event: dict) -> str:
    name       = event.get("event", "unknown")
    props      = event.get("properties", {})
    timestamp  = event.get("timestamp", "")
    distinct   = event.get("distinct_id", "anon")

    # Parse timestamp
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        time_str = dt.strftime("%H:%M:%S UTC")
    except Exception:
        time_str = timestamp

    emoji = event_emoji(name)

    # Build property lines — show the most useful ones
    interesting_keys = [
        "$current_url", "$pathname", "url",
        "$browser", "$os", "$device_type",
        "$referrer", "$referring_domain",
        "$screen_width", "$screen_height",
        "query", "make", "model", "year",       # vehiclefinder-specific
        "element_text", "tag_name",
    ]
    prop_lines = []
    for key in interesting_keys:
        val = props.get(key)
        if val and str(val).strip():
            label = key.lstrip("$").replace("_", " ").title()
            val_str = str(val)
            if len(val_str) > 80:
                val_str = val_str[:77] + "…"
            prop_lines.append(f"  <code>{label}</code>: {val_str}")

    # Distinct ID — show first 8 chars for privacy
    did_short = str(distinct)[:8] + "…" if len(str(distinct)) > 8 else distinct

    lines = [
        f"{emoji} <b>{name}</b>  <i>{time_str}</i>",
        f"  👤 <code>{did_short}</code>",
    ]
    if prop_lines:
        lines.extend(prop_lines)

    return "\n".join(lines)

# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    log.info("PostHog → Telegram bot starting (poll every %ds)", POLL_INTERVAL)
    send_telegram("🟢 <b>PostHog bot started</b> — streaming events live.")

    state = load_state()

    # On first run, seed with current newest event so we don't flood old history
    if state["last_timestamp"] is None:
        log.info("First run — seeding state from latest event")
        try:
            events = fetch_events(after=None)
            if events:
                state["last_timestamp"] = events[0]["timestamp"]
                state["seen_ids"] = [e["id"] for e in events]
                save_state(state)
                log.info("Seeded. Last event: %s", state["last_timestamp"])
        except Exception as e:
            log.error("Seed failed: %s", e)

    while True:
        try:
            events = fetch_events(after=state["last_timestamp"])

            # Filter already-seen events (handles overlap at boundary)
            new_events = [
                e for e in events
                if e.get("id") not in state["seen_ids"]
            ]

            # PostHog returns newest-first; send oldest-first for chronological order
            new_events.reverse()

            for event in new_events:
                msg = format_event(event)
                send_telegram(msg)
                log.info("Sent: %s (%s)", event.get("event"), event.get("id"))
                time.sleep(0.3)  # slight throttle to avoid Telegram rate limits

            if new_events:
                # Update state to the newest event we just processed
                latest = new_events[-1]
                state["last_timestamp"] = latest["timestamp"]
                state["seen_ids"].extend(e["id"] for e in new_events)
                save_state(state)

        except requests.HTTPError as e:
            log.error("PostHog HTTP error: %s", e)
            send_telegram(f"⚠️ PostHog API error: <code>{e}</code>")
        except Exception as e:
            log.error("Unexpected error: %s", e)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
