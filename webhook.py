from fastapi import FastAPI, Request, HTTPException
import requests
import os
import logging
import html
from datetime import datetime, timezone
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

app = FastAPI()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SKIP_EVENTS = {
    "$web_vitals", "web vitals",
    "$autocapture", "clicked i",
    "$pageleave", "pageleave",
}

@app.on_event("startup")
async def startup_event():
    send_telegram("PostHog webhook service online")

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=10)
        response.raise_for_status()
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")

def get_fuzzy(data, key):
    if not isinstance(data, dict):
        return None
    target = key.lower().replace("$", "").replace("_", "").replace(" ", "")
    for k, v in data.items():
        if k.lower().replace("$", "").replace("_", "").replace(" ", "") == target:
            return v
    return None

def esc(val) -> str:
    return html.escape(str(val)) if val is not None else ""

@app.post("/posthog")
async def posthog_webhook(req: Request):
    try:
        data = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_val = get_fuzzy(data, "event")
    if isinstance(event_val, dict):
        raw_event   = str(get_fuzzy(event_val, "event") or "unknown")
        props       = get_fuzzy(event_val, "properties") or {}
        distinct_id = str(get_fuzzy(event_val, "distinct id") or get_fuzzy(data, "distinct id") or "anon")
    else:
        raw_event   = str(event_val or "unknown")
        props       = get_fuzzy(data, "properties") or {}
        distinct_id = str(get_fuzzy(data, "distinct id") or "anon")

    if not event_val and not props:
        return {"ok": True}

    if raw_event.lower().strip() in SKIP_EVENTS:
        logger.info(f"Skipped: {raw_event}")
        return {"ok": True}

    city     = get_fuzzy(props, "geoip city name")
    country  = get_fuzzy(props, "geoip country name")
    page_url = get_fuzzy(props, "current url")
    browser  = get_fuzzy(props, "browser")
    os_name  = get_fuzzy(props, "os")
    make     = get_fuzzy(props, "make")
    model    = get_fuzzy(props, "model")
    year     = get_fuzzy(props, "year")

    clean_event = raw_event.replace("$", "").replace("_", " ").title()
    short_id    = distinct_id[:8] + "…" if len(distinct_id) > 8 else distinct_id
    location    = f"{city}, {country}" if city and country else "Unknown location"
    time_str    = datetime.now(timezone.utc).strftime("%H:%M:%S")

    site_label = ""
    if page_url:
        if "vehiclefinder.co.nz" in page_url:
            site_label = "VF · "
        elif "jedbillyb.com" in page_url:
            site_label = "JB · "

    lines = [f"<b>{site_label}{esc(clean_event)}</b>  <code>{time_str} UTC</code>"]

    if make and model:
        vehicle = f"{year} {make} {model}".strip() if year else f"{make} {model}"
        lines.append(f"<b>{esc(vehicle)}</b>")

    lines.append(f"<code>{esc(short_id)}</code>  ·  {esc(location)}")

    if page_url:
        display_url = page_url
        for known in ("vehiclefinder.co.nz", "jedbillyb.com"):
            if known in page_url:
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(page_url)
                    display_url = parsed.path + (f"?{parsed.query}" if parsed.query else "")
                except Exception:
                    pass
                break
        lines.append(f"<code>{esc(display_url)}</code>")

    if browser or os_name:
        device = "  ·  ".join(filter(None, [browser, os_name]))
        lines.append(esc(device))

    msg = "\n".join(lines)
    send_telegram(msg)
    return {"ok": True}
