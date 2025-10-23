import os, hmac, hashlib, pathlib, re
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Any, Dict

import requests
from fastapi import FastAPI, Header, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import pytz
from datetime import timezone, timedelta

load_dotenv()

WEBEX_ACCESS_TOKEN = os.getenv("WEBEX_ACCESS_TOKEN")
WEBEX_WEBHOOK_SECRET = os.getenv("WEBEX_WEBHOOK_SECRET", "yoursecret")
LOG_DIR = os.getenv("LOG_DIR", "./logs")

HEADERS = {"Authorization": f"Bearer {WEBEX_ACCESS_TOKEN}"}

app = FastAPI(title="Webex Bot Webhook (FastAPI)")
pathlib.Path(LOG_DIR).mkdir(parents=True, exist_ok=True)

# --- เรียกดูข้อมูลตัวบอท (personId) เพื่อกันลูปตอบเอง ---
ME = requests.get("https://webexapis.com/v1/people/me", headers=HEADERS).json()
BOT_PERSON_ID = os.getenv("WEBEX_BOT_EMAIL")
print(f"Me: {ME}")
print(f"Bot Person ID: {BOT_PERSON_ID}")


def verify_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """ตรวจ HMAC-SHA1 จาก X-Spark-Signature"""
    if not signature_header:
        return False
    mac = hmac.new(WEBEX_WEBHOOK_SECRET.encode(), msg=raw_body, digestmod=hashlib.sha1)
    return hmac.compare_digest(signature_header, mac.hexdigest())

def sanitize_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.@+-]", "_", name)

TZ = timezone(timedelta(hours=7))

def to_th_time(iso_utc: str) -> str:
    # "2025-10-23T15:30:00.000Z" -> "2025-10-23 22:30:00 +07:00"
    dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00")).astimezone(TZ)
    return dt.strftime("%Y-%m-%d %H:%M:%S %z")

def webex_get(url: str) -> Dict[str, Any]:
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    return r.json()

def webex_post(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.post(url, headers=HEADERS, json=payload, timeout=10)
    r.raise_for_status()
    return r.json()

def get_message(message_id: str) -> Dict[str, Any]:
    return webex_get(f"https://webexapis.com/v1/messages/{message_id}")

def get_room_title(room_id: str) -> str:
    try:
        return webex_get(f"https://webexapis.com/v1/rooms/{room_id}").get("title", "")
    except Exception:
        return ""

def get_person_email(person_id: str, fallback: str = "") -> str:
    if fallback:
        return fallback
    try:
        p = webex_get(f"https://webexapis.com/v1/people/{person_id}")
        if p.get("emails"):
            return p["emails"][0]
    except Exception:
        pass
    return "unknown@example.com"

def append_user_log(email: str, line: str) -> None:
    print(email)
    print(line)
    fn = os.path.join(LOG_DIR, sanitize_filename(email) + ".log")
    with open(fn, "a", encoding="utf-8") as f:
        f.write(line)

def reply(room_id: str, markdown: str) -> None:
    webex_post("https://webexapis.com/v1/messages", {"roomId": room_id, "markdown": markdown})

def process_event_async(event: Dict[str, Any]) -> None:
    """งานเบื้องหลัง: ดึงข้อความจริง, เขียน log, (ออปชัน) ตอบกลับ"""
    data = event.get("data", {})
    print(data)
    if not data:
        return
    # if data.get("personId") == BOT_PERSON_ID:
    #     # ข้ามข้อความจากบอทเอง
    #     return
    if data.get("personEmail") == BOT_PERSON_ID:
        # Message is from the bot. Log the preceding user message and the bot's reply together.
        room_id = data.get("roomId")
        if not room_id:
            return  # Cannot proceed without a room ID

        try:
            # Fetch the last 2 messages. The list is sorted newest first.
            # items[0] is the bot's message, items[1] is the user's message before it.
            messages_url = f"https://webexapis.com/v1/messages?roomId={room_id}&max=2"
            messages_response = webex_get(messages_url)
            items = messages_response.get("items", [])

            if len(items) < 2:
                return # Not enough message history
            print("---------------------------------------------")
            print(items)
            print("---------------------------------------------")

            bot_message = items[0]
            user_message = items[1]

            # To prevent loops, ensure the previous message is not from the bot.
            if user_message.get("personId") == BOT_PERSON_ID:
                return

            # Get common details
            room_title = get_room_title(room_id)
            bot_email = BOT_PERSON_ID # Filename for the bot's log

            # User message details
            user_email = get_person_email(user_message.get("personId"), user_message.get("personEmail"))
            user_text = (user_message.get("text") or "").strip()
            user_when_th = to_th_time(user_message.get("created", ""))
            
            # Bot message details
            bot_text = (bot_message.get("text") or "").strip()
            bot_when_th = to_th_time(bot_message.get("created", ""))

            # Prepare log content with both messages
            user_log_line = f"{user_when_th} | Room: {room_title} | {user_email}: {user_text}\n"
            bot_log_line = f"{bot_when_th} | Room: {room_title} | Bot: {bot_text}\n"
            
            # Append both lines to the bot's log file
            append_user_log(bot_email, user_log_line + bot_log_line)

        except Exception as e:
            print(f"Error logging bot conversation: {e}")
        
        # Stop further processing for this bot message event
        return

    # 1) ดึงข้อความจริง
    msg = get_message(data["id"])
    text = (msg.get("text") or msg.get("markdown") or "").strip()
    created = msg.get("created", "")
    when_th = to_th_time(created) if created else ""
    room_id = msg.get("roomId", "")
    sender_email = get_person_email(data.get("personId", ""), data.get("personEmail", ""))

    # 2) optional: ดึงชื่อห้องไว้ใน log
    room_title = get_room_title(room_id)

    # 3) เขียน log ต่อผู้ใช้
    line = f"{when_th} | Room: {room_title} | {text}\n"
    append_user_log(sender_email, line)

    # 4) (ออปชัน) ตอบกลับสั้นๆ เวลาเริ่มต้นทดลอง
    # reply(room_id, f"รับแล้วจาก **{sender_email}**: `{text}`")

@app.get("/health")
def health():
    return {"ok": True}

#@app.post("/webex/webhook")
@app.post("/")
async def webex_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_spark_signature: str | None = Header(default=None)
):
    raw = await request.body()

    # 1) ตรวจลายเซ็นก่อน
    if not verify_signature(raw, x_spark_signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    event = await request.json()
    if event.get("resource") != "messages" or event.get("event") != "created":
        return JSONResponse({"ignored": True})

    # 2) สั่งทำงานเบื้องหลัง แล้วตอบ 200 ทันที
    background_tasks.add_task(process_event_async, event)
    return JSONResponse({"status": "ok"})
