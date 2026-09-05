import os
import json
import random
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT_BOT_TOKEN_HERE")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
DATA_FILE = Path(os.getenv("DATA_FILE", "data.json"))

DEFAULT_PAYMENT_MESSAGE = """💳 اطلاعات واریز 💳

🔥 لطفاً مبلغ هر تعداد محصول رو خواستید از داخل پیج جمع بزنید ➕ 120 هزار تومان هزینه ارسال را به مشخصات زیر واریز نمایید:
🔹 شماره کارت: 6219861353342933
🔹 بنام:فاطمه زهرا روشنی
💡 نکته: تعداد محصول تاثیری روی هزینه پست نداره؛ کل سفارش شما فقط با یک هزینه ارسال، ثبت نهایی میشه.
⚠️ (در صورت بروز اختلال در اپلیکیشن‌های مثل آپ، از همراه بانک یا سایر برنامه‌ها استفاده کنید).

⏳زمان تحویل مرسوله 5 روز کاری هست بین 1 تا 2 روز هم ارسال محصول‌تون زمان می‌بره."""

ORDER_FORM = """🌱 خیلی خوشحالیم که ما رو انتخاب کردید!
واسه اینکه بسته‌تون سریع‌تر آماده‌ی ارسال بشه، این فرم رو پر کنید و برامون بفرستید:
👤 نام و فامیل:
📱 شماره تماس:
📍 آدرس دقیق (شهر + پلاک + واحد):
📮 کد پستی:
📐 سایز دقیق آیتم انتخابی:"""

FINAL_MESSAGE = """🔥 تأیید واریزی و ثبت نهایی 🔥

دمت گرم بابت انتخاب و اعتمادت به بوتیک ما! 👑👊🏼

📦 زمان‌بندی ارسال: آیتمت رفت واسه بخش پکینگ؛ روزهای عادی همون فردای واریزی برات شیپ میشه. فقط حواست باشه توی روزهای تعطیل رسمی، ارسال میافته واسه اولین روز کاریِ بعدش (مثلاً اگه پنجشنبه ثبت کنی، شنبه ارسال میشه). 🚚⚡️

امیدواریم از این خرید کلی لذت ببری و برات خوش‌یمن باشه. روزیت افزون! 🪐💰"""

SIZE_GUIDE = """📐 SIZE GUIDE / راهنمای سایز آیتم‌ها 📐
اعداد بر اساس سانتی‌متر هستن. واسه فیتِ دقیق، یکی از تیشرت‌ها یا هودی‌های خودت رو پهن کن و عرض و قدش رو متر بزن ⬇️

⚡️ هـودی (Hoodie)
▫️ S ▫️ عرض سینه: ۹۰-۹۵ | سرشانه: ۴۰-۴۲ | قد کار: ۶۸-۷۰
▫️ M ▫️ عرض سینه: ۹۶-۱۰۰ | سرشانه: ۴۲-۴۴ | قد کار: ۷۰-۷۲
▫️ L ▫️ عرض سینه: ۱۰۱-۱۰۵ | سرشانه: ۴۴-۴۶ | قد کار: ۷۲-۷۴
▫️ XL ▫️ عرض سینه: ۱۰۶-۱۱۰ | سرشانه: ۴۶-۴۸ | قد کار: ۷۴-۷۶
▫️ XXL ▫️ عرض سینه: ۱۱۱-۱۱۵ | سرشانه: ۴۸-۵۰ | قد کار: ۷۶-۷۸
▫️ 3XL ▫️ عرض سینه: ۱۱۶-۱۲۰ | سرشانه: ۵۰-۵۲ | قد کار: ۷۸-۸۰

⚡️ کـاپـشن (Jacket)
▪️ S ▪️ عرض سینه: ۹۲-۹۸ | قد کار: ۶۸-۷۲ | شانه تا کمر: ۴۰-۴۲
▪️ M ▪️ عرض سینه: ۹۹-۱۰۵ | قد کار: ۷۰-۷۴ | شانه تا کمر: ۴۲-۴۴
▪️ L ▪️ عرض سینه: ۱۰۶-۱۱۲ | قد کار: ۷۲-۷۶ | شانه تا کمر: ۴۴-۴۶
▪️ XL ▪️ عرض سینه: ۱۱۳-۱۱۹ | قد کار: ۷۴-۷۸ | شانه تا کمر: ۴۶-۴۸
▪️ XXL ▪️ عرض سینه: ۱۲۰-۱۲۶ | قد کار: ۷۶-۸۰ | شانه تا کمر: ۴۸-۵۰

⚡️ تی‌شـرت (T-Shirt)
▫️ S ▫️ عرض سینه: ۸۴-۸۸ | قد کار: ۶۴-۶۶
▫️ M ▫️ عرض سینه: ۸۹-۹۳ | قد کار: ۶۶-۶۸
▫️ L ▫️ عرض سینه: ۹۴-۹۸ | قد کار: ۶۸-۷۰
▫️ XL ▫️ عرض سینه: ۹۹-۱۰۳ | قد کار: ۷۰-۷۲
▫️ XXL ▫️ عرض سینه: ۱۰۴-۱۰۸ | قد کار: ۷۲-۷۴

⚡️ دورس (Sweatshirt)
▪️ S ▪️ عرض سینه: ۷۸-۸۲ | آستین: ۱۸-۲۰ | قد کار: ۷۲-۷۶
▪️ M ▪️ عرض سینه: ۸۳-۸۷ | آستین: ۲۰-۲۲ | قد کار: ۷۴-۷۸
▪️ L ▪️ عرض سینه: ۸۸-۹۲ | آستین: ۲۲-۲۴ | قد کار: ۷۶-۸۰
▪️ XL ▪️ عرض سینه: ۹۳-۹۷ | آستین: ۲۴-۲۶ | قد کار: ۷۸-۸۲
▪️ XXL ▪️ عرض سینه: ۹۸-۱۰۲ | آستین: ۲۶-۲۸ | قد کار: ۸۰-۸۴

⚡️ بـادگـیر (Windbreaker)
▫️ S ▫️ عرض سینه: ۸۸-۹۲ | قد کار: ۷۰-۷۴
▫️ M ▫️ عرض سینه: ۹۳-۹۷ | قد کار: ۷۴-۷۸
▫️ L ▫️ عرض سینه: ۹۸-۱۰۲ | قد کار: ۷۸-۸۲
▫️ XL ▫️ عرض سینه: ۱۰۳-۱۰۷ | قد کار: ۸۲-۸۶
▫️ XXL ▫️ عرض سینه: ۱۰۸-۱۱۲ | قد کار: ۸۶-۹۰

⚡️ وِسـت / ژیله (Vest)
▫️ S ▫️ عرض سینه: ۹۰-۹۴ | قد کار: ۶۶-۶۸
▫️ M ▫️ عرض سینه: ۹۵-۹۹ | قد کار: ۶۸-۷۰
▫️ L ▫️ عرض سینه: ۱۰۰-۱۰۴ | قد کار: ۷۰-۷۲
▫️ XL ▫️ عرض سینه: ۱۰۵-۱۰۹ | قد کار: ۷۲-۷۴
▫️ XXL ▫️ عرض سینه: ۱۱۰-۱۱۴ | قد کار: ۷۴-۷۶
▫️ 3XL ▫️ عرض سینه: ۱۱۵-۱۲۰ | قد کار: ۷۶-۷۸

⚡️ شـلـوار (Pants / Jeans)
▫️ S ▫️ دور کمر: ۷۵-۸۰ | قد کار: ۱۰۰-۱۰۲
▫️ M ▫️ دور کمر: ۸۱-۸۶ | قد کار: ۱۰۲-۱۰۴
▫️ L ▫️ دور کمر: ۸۷-۹۲ | قد کار: ۱۰۴-۱۰۶
▫️ XL ▫️ دور کمر: ۹۳-۹۸ | قد کار: ۱۰۶-۱۰۸
▫️ XXL ▫️ دور کمر: ۹۹-۱۰۴ | قد کار: ۱۰۸-۱۱۰
▫️ 3XL ▫️ دور کمر: ۱۰۵-۱۱۰ | قد کار: ۱۱۰-۱۱۲

سایزبندی بادی 📏

S
عرض سینه: ۳۶ تا ۳۸
قد: ۶۸ تا ۷۰
عرض کمر: ۳۰ تا ۳۲

M
عرض سینه: ۳۸ تا ۴۰
قد: ۷۰ تا ۷۲
عرض کمر: ۳۲ تا ۳۴

L
عرض سینه: ۴۰ تا ۴۲
قد: ۷۲ تا ۷۴
عرض کمر: ۳۴ تا ۳۶

XL
عرض سینه: ۴۲ تا ۴۵
قد: ۷۴ تا ۷۶
عرض کمر: ۳۶ تا ۳۹

2XL
عرض سینه: ۴۵ تا ۴۸
قد: ۷۶ تا ۷۸
عرض کمر: ۳۹ تا ۴۲

3XL
عرض سینه: ۴۸ تا ۵۱
قد: ۷۸ تا ۸۰
عرض کمر: ۴۲ تا ۴۵

4XL
عرض سینه: ۵۱ تا ۵۴
قد: ۸۰ تا ۸۲
عرض کمر: ۴۵ تا ۴۸

📌 تمامی اندازه‌ها به سانتی‌متر و در حالت خوابیده هستند."""

PRICE_REPLY = "قیمت داخل پیج گذاشتیم 🌹"
VOICE_REPLY = "لطفاً پیامتون رو تایپ کنید 🌹"
FIRST_REPLY = "سلام، بله چه محصولی می‌خوایید؟"
SECOND_REPLY = "بله موجوده ✅"
SECOND_REPLY_DELAY = int(os.getenv("SECOND_REPLY_DELAY", "60"))
WELCOME_REPLIES = [
    "سلام، خوش اومدی 🌹 در خدمتم.",
    "سلام عزیز، خوش اومدی 🌹 بگو چطور راهنماییت کنم.",
    "سلام و خوش اومدی 🌱 در خدمتم.",
]
AVAILABLE_REPLIES = [
    "بله عزیز، همه محصولات موجودن ✅",
    "آره، در حال حاضر همه محصولات موجودن ✅",
    "بله، تمامی محصولات داخل پیج موجودن 🌹",
]
PHOTO_BATCH_REPLIES = [
    "عکس محصول ثبت شد ✅ بریم برای ادامه سفارش.",
    "عکس‌هایی که فرستادی ثبت شدن ✅ بریم برای ادامه سفارش.",
    "همه عکس‌های محصول رو ثبت کردم ✅ حالا بریم ادامه سفارش.",
]
RECEIPT_REMINDERS = [
    "بعد از واریز فقط عکس رسید رو همینجا بفرست لطفاً 🌹",
    "منتظر عکس رسیدت هستم تا سفارشت نهایی بشه ✅",
    "هر وقت واریز انجام شد، عکس رسید رو همینجا ارسال کن 🌱",
]

SIZE_WORDS = [
    "سایز", "سايز", "سایض", "سایذ", "سایس", "سایژ", "سایظ", "سایزبندی", "سایز بندی",
    "راهنمای سایز", "راهنما سایز", "جدول سایز", "جدول سایزبندی", "اندازه", "سایزم", "سایزش",
    "چه سایزی", "چه سایز", "سایزم چیه", "سایزش چیه", "سایز مناسب", "اندازه مناسب", "فیت",
    "تن خور", "تنخور", "دور سینه", "عرض سینه", "قد کار", "دور کمر", "عرض کمر", "سرشانه",
    "xl", "xxl", "2xl", "3xl", "4xl", "اسمال", "مدیوم", "لارج", "اکس لارج", "ایکس لارج",
    "size", "sizing"
]
PRICE_WORDS = ["قیمت", "قيمت", "قیمط", "قیمتش", "چنده", "price"]
ORDER_WORDS = [
    "سفارش", "ثبت سفارش", "میخوام", "می خوام", "می‌خوام", "خرید", "بخرم",
    "باشه", "اوکی", "اوکیه", "بله", "آره", "ادامه", "فرم", "شماره کارت",
]
RECEIPT_WORDS = ["رسید", "واریز", "پرداخت", "کارت به کارت", "کارت‌به‌کارت"]


def default_data() -> Dict[str, Any]:
    return {
        "payment_message": DEFAULT_PAYMENT_MESSAGE,
        "payment_messages": [],
        "awaiting_payment_edit": False,
        "business_connections": {},
        "pending_order": {},
    }


def load_data() -> Dict[str, Any]:
    if DATA_FILE.exists():
        try:
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            base = default_data()
            base.update(data)
            return base
        except Exception:
            pass
    return default_data()


def save_data(data: Dict[str, Any]) -> None:
    DATA_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def api(method: str, payload: Optional[Dict[str, Any]] = None, timeout: int = 30) -> Dict[str, Any]:
    r = requests.post(f"{BASE_URL}/{method}", json=payload or {}, timeout=timeout)
    result = r.json()
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API {method}: {result}")
    return result["result"]


def normalize(text: str) -> str:
    text = (text or "").strip().lower()
    text = text.replace("ي", "ی").replace("ك", "ک")
    text = re.sub(r"\s+", " ", text)
    return text


def contains_any(text: str, words: List[str]) -> bool:
    return any(normalize(w) in text for w in words)


def is_size_request(text: str) -> bool:
    t = normalize(text)
    compact = re.sub(r"[\s\u200c\-_/.,!?؟]+", "", t)
    if contains_any(t, SIZE_WORDS):
        return True
    if any(root in compact for root in ("سایز", "سايز", "سایس", "سایض", "سایذ", "سایژ", "سایظ")):
        return True
    return bool(re.search(r"(?<![a-z0-9])(?:s|m|l|xl|xxl|xxxl|[234]xl)(?![a-z0-9])", t, re.I))


def admin_keyboard() -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [{"text": "✏️ تغییر پیام ۲", "callback_data": "edit_payment"}],
            [{"text": "🗑 حذف پیام شماره کارت از چت‌ها", "callback_data": "delete_payment"}],
            [{"text": "👁 نمایش پیام ۲ فعلی", "callback_data": "show_payment"}],
        ]
    }


def send_admin(text: str, keyboard: Optional[Dict[str, Any]] = None) -> None:
    if not ADMIN_ID:
        return
    payload: Dict[str, Any] = {"chat_id": ADMIN_ID, "text": text}
    if keyboard:
        payload["reply_markup"] = keyboard
    api("sendMessage", payload)


def send_business(connection_id: str, chat_id: int, text: str) -> Dict[str, Any]:
    return api("sendMessage", {
        "business_connection_id": connection_id,
        "chat_id": chat_id,
        "text": text,
    })


def new_chat_state() -> Dict[str, Any]:
    """Return a durable per-customer state for the sales conversation."""
    return {
        "step": "new",
        "sent_keys": [],
        "product_photos": [],
        "inbound_turns": 0,
        "last_photo_at": 0,
        "last_media_group_id": None,
        "receipt_reminder_index": 0,
        "processed_message_ids": [],
        "replied_message_ids": [],
        "sent_texts": [],
        "availability_due": 0,
        "availability_message_id": 0,
    }


def get_chat_state(pending: Dict[str, Any], state_key: str) -> Dict[str, Any]:
    """Load state and safely migrate the boolean/string format of older versions."""
    old = pending.get(state_key)
    if isinstance(old, dict):
        state = new_chat_state()
        state.update(old)
        return state

    state = new_chat_state()
    if old == "awaiting_receipt":
        state["step"] = "awaiting_receipt"
        state["sent_keys"] = ["welcome", "available", "order_form", "payment"]
        state["inbound_turns"] = 3
    elif old is True:
        state["step"] = "available"
        state["sent_keys"] = ["welcome", "available"]
        state["inbound_turns"] = 2
    pending[state_key] = state
    return state


def send_once(
    connection_id: str,
    chat_id: int,
    state: Dict[str, Any],
    key: str,
    text: str,
) -> Optional[Dict[str, Any]]:
    """Send important sales text at most once in each customer chat."""
    sent = state.setdefault("sent_keys", [])
    if key in sent:
        return None
    result = send_business(connection_id, chat_id, text)
    sent.append(key)
    return result


def remember_ids(values: List[int], limit: int = 500) -> List[int]:
    """Keep durable deduplication data bounded."""
    return values[-limit:]


def mark_messages_processed(state: Dict[str, Any], messages: List[Dict[str, Any]]) -> bool:
    """Return False if this Telegram message/album was already handled."""
    processed = [int(x) for x in state.setdefault("processed_message_ids", [])]
    incoming = [int(m.get("message_id") or 0) for m in messages]
    incoming = [mid for mid in incoming if mid]
    if incoming and all(mid in processed for mid in incoming):
        return False
    for mid in incoming:
        if mid not in processed:
            processed.append(mid)
    state["processed_message_ids"] = remember_ids(processed)
    return True


def send_state_reply(
    connection_id: str,
    chat_id: int,
    state: Dict[str, Any],
    message_id: int,
    text: str,
) -> Optional[Dict[str, Any]]:
    """Enforce one reply per inbound message and no repeated reply text per chat."""
    replied = [int(x) for x in state.setdefault("replied_message_ids", [])]
    sent_texts = state.setdefault("sent_texts", [])
    message_id = int(message_id or 0)
    clean_text = (text or "").strip()
    if not clean_text or (message_id and message_id in replied) or clean_text in sent_texts:
        return None
    result = send_business(connection_id, chat_id, clean_text)
    if message_id:
        replied.append(message_id)
    sent_texts.append(clean_text)
    state["replied_message_ids"] = remember_ids(replied)
    state["sent_texts"] = sent_texts[-100:]
    return result


def is_order_request(text: str) -> bool:
    t = normalize(text)
    return any(normalize(word) in t for word in ORDER_WORDS)


def process_due_availability_replies() -> None:
    """Send minute-delayed replies without pausing the polling loop."""
    data = load_data()
    pending = data.setdefault("pending_order", {})
    now = int(time.time())
    changed = False
    for state_key, raw_state in list(pending.items()):
        if not isinstance(raw_state, dict):
            continue
        state = get_chat_state(pending, state_key)
        if state.get("step") != "availability_pending":
            continue
        if int(state.get("availability_due") or 0) > now:
            continue
        try:
            connection_id, raw_chat_id = state_key.rsplit(":", 1)
            chat_id = int(raw_chat_id)
        except (ValueError, TypeError):
            continue
        message_id = int(state.get("availability_message_id") or 0)
        send_state_reply(connection_id, chat_id, state, message_id, SECOND_REPLY)
        state["step"] = "available"
        state["availability_due"] = 0
        state["availability_message_id"] = 0
        pending[state_key] = state
        changed = True
    if changed:
        save_data(data)


def extract_image_file_id(msg: Dict[str, Any]) -> Optional[str]:
    photos = msg.get("photo") or []
    if photos:
        return photos[-1].get("file_id")
    doc = msg.get("document") or {}
    if (doc.get("mime_type") or "").lower().startswith("image/"):
        return doc.get("file_id")
    return None


def handle_business_connection(conn: Dict[str, Any]) -> None:
    data = load_data()
    cid = conn.get("id")
    if not cid:
        return
    user = conn.get("user") or {}
    rights = conn.get("rights") or {}
    data["business_connections"][cid] = {
        "user_id": user.get("id"),
        "is_enabled": conn.get("is_enabled", True),
        "rights": rights,
    }
    save_data(data)
    if conn.get("is_enabled"):
        try:
            send_admin("✅ ربات با موفقیت به اکانت Telegram Business وصل شد.", admin_keyboard())
        except Exception:
            pass


def is_business_owner_message(msg: Dict[str, Any], data: Dict[str, Any]) -> bool:
    cid = msg.get("business_connection_id")
    owner_id = (data.get("business_connections", {}).get(cid) or {}).get("user_id")
    sender_id = (msg.get("from") or {}).get("id")
    return bool(owner_id and sender_id == owner_id)


def forward_receipt_to_admin(msg: Dict[str, Any]) -> bool:
    if not ADMIN_ID:
        return False
    user = msg.get("from") or {}
    name = " ".join(filter(None, [user.get("first_name"), user.get("last_name")])).strip() or "بدون نام"
    username = f"@{user['username']}" if user.get("username") else "ندارد"
    caption = f"🧾 رسید جدید\nنام: {name}\nیوزرنیم: {username}\nآیدی: {user.get('id', '-') }"

    photos = msg.get("photo") or []
    if photos:
        api("sendPhoto", {"chat_id": ADMIN_ID, "photo": photos[-1]["file_id"], "caption": caption})
        return True

    doc = msg.get("document")
    if doc:
        mime = (doc.get("mime_type") or "").lower()
        if mime.startswith("image/"):
            api("sendDocument", {"chat_id": ADMIN_ID, "document": doc["file_id"], "caption": caption})
            return True
    return False


def _legacy_handle_business_message(msg: Dict[str, Any], grouped_messages: Optional[List[Dict[str, Any]]] = None) -> None:
    data = load_data()
    if is_business_owner_message(msg, data):
        return

    connection_id = msg.get("business_connection_id")
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    if not connection_id or chat_id is None:
        return

    # Track a complete, durable conversation stage per business chat.
    state_key = f"{connection_id}:{chat_id}"
    pending = data.setdefault("pending_order", {})
    state = get_chat_state(pending, state_key)
    stage = state.get("step", "new")

    # Telegram albums arrive as multiple updates. Treat the whole album as one
    # customer turn and save every photo, instead of mistaking later photos for receipts.
    media_messages = grouped_messages or [msg]
    image_ids = [extract_image_file_id(item) for item in media_messages]
    image_ids = [file_id for file_id in image_ids if file_id]
    if image_ids:
        if stage == "awaiting_receipt":
            # Only the first image is needed as the payment receipt. Telegram albums
            # are forwarded completely so the admin never loses an attached image.
            forwarded = False
            for item in media_messages:
                forwarded = forward_receipt_to_admin(item) or forwarded
            if forwarded:
                send_once(connection_id, chat_id, state, "final", FINAL_MESSAGE)
                state["step"] = "completed"
                pending[state_key] = state
                save_data(data)
            return

        known_photos = state.setdefault("product_photos", [])
        for file_id in image_ids:
            if file_id not in known_photos:
                known_photos.append(file_id)

        now = int(msg.get("date") or time.time())
        media_group_id = msg.get("media_group_id")
        same_photo_batch = bool(
            (media_group_id and media_group_id == state.get("last_media_group_id"))
            or (not media_group_id and now - int(state.get("last_photo_at") or 0) <= 8)
        )
        state["last_photo_at"] = now
        state["last_media_group_id"] = media_group_id

        if not same_photo_batch:
            state["inbound_turns"] = int(state.get("inbound_turns") or 0) + 1

        turns = int(state.get("inbound_turns") or 0)
        if turns == 1:
            count_text = "عکست" if len(known_photos) == 1 else f"هر {len(known_photos)} عکست"
            welcome = f"سلام، خوش اومدی 🌹 {count_text} به‌عنوان عکس محصول ثبت شد ✅"
            send_once(connection_id, chat_id, state, "welcome", welcome)
            state.setdefault("sent_keys", []).append("photo_ack")
            state["step"] = "greeted"
        elif turns == 2:
            send_once(connection_id, chat_id, state, "available", random.choice(AVAILABLE_REPLIES))
            state["step"] = "available"
        elif "photo_ack" not in state.setdefault("sent_keys", []):
            photo_reply = PHOTO_BATCH_REPLIES[0] if len(known_photos) == 1 else random.choice(PHOTO_BATCH_REPLIES[1:])
            send_once(connection_id, chat_id, state, "photo_ack", photo_reply)

        pending[state_key] = state
        save_data(data)
        return

    # Voice/audio is still a customer turn, but the first two replies always keep
    # the requested greeting -> availability order.
    is_voice = bool(msg.get("voice") or msg.get("audio"))

    text = normalize(msg.get("text") or msg.get("caption") or "")
    if not text and not is_voice:
        return

    state["inbound_turns"] = int(state.get("inbound_turns") or 0) + 1
    turns = int(state["inbound_turns"])

    # Exact requested opening: first customer turn gets a greeting; on their
    # second turn the bot says that every product is available.
    if turns == 1:
        send_once(connection_id, chat_id, state, "welcome", random.choice(WELCOME_REPLIES))
        state["step"] = "greeted"
        pending[state_key] = state
        save_data(data)
        return

    if turns == 2:
        send_once(connection_id, chat_id, state, "available", random.choice(AVAILABLE_REPLIES))
        state["step"] = "available"
        pending[state_key] = state
        save_data(data)
        return

    if is_voice:
        if "voice_request" not in state.setdefault("sent_keys", []):
            send_once(connection_id, chat_id, state, "voice_request", VOICE_REPLY)
        pending[state_key] = state
        save_data(data)
        return

    # Size questions get only size guide, with no forced order step.
    if is_size_request(text):
        send_once(connection_id, chat_id, state, "size_guide", SIZE_GUIDE)
        pending[state_key] = state
        save_data(data)
        return

    # Price questions get only the fixed price answer.
    if contains_any(text, PRICE_WORDS):
        send_once(connection_id, chat_id, state, "price_reply", PRICE_REPLY)
        pending[state_key] = state
        save_data(data)
        return

    if stage == "completed":
        # The order is already complete. Never restart and resend old sales texts.
        pending[state_key] = state
        save_data(data)
        return

    if stage == "awaiting_receipt":
        reminder_index = int(state.get("receipt_reminder_index") or 0)
        if reminder_index < len(RECEIPT_REMINDERS):
            send_business(connection_id, chat_id, RECEIPT_REMINDERS[reminder_index])
            state["receipt_reminder_index"] = reminder_index + 1
        pending[state_key] = state
        save_data(data)
        return

    # After greeting and availability, send the order form and payment details once.
    send_once(connection_id, chat_id, state, "order_form", ORDER_FORM)
    payment_msg = send_once(
        connection_id,
        chat_id,
        state,
        "payment",
        data.get("payment_message", DEFAULT_PAYMENT_MESSAGE),
    )

    if payment_msg:
        data.setdefault("payment_messages", []).append({
            "business_connection_id": connection_id,
            "chat_id": chat_id,
            "message_id": payment_msg.get("message_id"),
        })
    state["step"] = "awaiting_receipt"
    pending[state_key] = state
    save_data(data)


def handle_business_message(msg: Dict[str, Any], grouped_messages: Optional[List[Dict[str, Any]]] = None) -> None:
    """Deterministic conversation flow with delayed availability and strict deduplication."""
    data = load_data()
    if is_business_owner_message(msg, data):
        return

    connection_id = msg.get("business_connection_id")
    chat_id = (msg.get("chat") or {}).get("id")
    if not connection_id or chat_id is None:
        return

    state_key = f"{connection_id}:{chat_id}"
    pending = data.setdefault("pending_order", {})
    state = get_chat_state(pending, state_key)
    media_messages = grouped_messages or [msg]

    if not mark_messages_processed(state, media_messages):
        return

    # Safely migrate states written by the previous revision of this same file.
    if state.get("step") == "greeted":
        state["step"] = "waiting_second_message"

    message_id = int(msg.get("message_id") or 0)
    image_ids = [extract_image_file_id(item) for item in media_messages]
    image_ids = [file_id for file_id in image_ids if file_id]
    if image_ids:
        known = state.setdefault("product_photos", [])
        for file_id in image_ids:
            if file_id not in known:
                known.append(file_id)

    stage = state.get("step", "new")

    # First customer message: immediate fixed reply.
    if stage == "new":
        send_state_reply(connection_id, chat_id, state, message_id, FIRST_REPLY)
        state["step"] = "waiting_second_message"
        pending[state_key] = state
        save_data(data)
        return

    # Second customer message: schedule exactly one minute later and return now.
    if stage == "waiting_second_message":
        state["step"] = "availability_pending"
        state["availability_due"] = int(time.time()) + max(1, SECOND_REPLY_DELAY)
        state["availability_message_id"] = message_id
        pending[state_key] = state
        save_data(data)
        return

    # Messages arriving during the minute are recorded but receive no premature reply.
    if stage == "availability_pending":
        pending[state_key] = state
        save_data(data)
        return

    # After payment details have been sent, photos are receipts. Before that,
    # every received photo remains registered as a product photo.
    if image_ids:
        if stage == "awaiting_receipt":
            forwarded = False
            for item in media_messages:
                forwarded = forward_receipt_to_admin(item) or forwarded
            if forwarded:
                send_state_reply(connection_id, chat_id, state, message_id, FINAL_MESSAGE)
                state["step"] = "completed"
        elif stage == "available":
            reply = PHOTO_BATCH_REPLIES[0] if len(image_ids) == 1 else PHOTO_BATCH_REPLIES[1]
            send_state_reply(connection_id, chat_id, state, message_id, reply)
        pending[state_key] = state
        save_data(data)
        return

    text = normalize(msg.get("text") or msg.get("caption") or "")
    is_voice = bool(msg.get("voice") or msg.get("audio"))
    if not text and not is_voice:
        pending[state_key] = state
        save_data(data)
        return

    if stage == "completed":
        pending[state_key] = state
        save_data(data)
        return

    if is_voice:
        send_state_reply(connection_id, chat_id, state, message_id, VOICE_REPLY)
        pending[state_key] = state
        save_data(data)
        return

    if is_size_request(text):
        send_state_reply(connection_id, chat_id, state, message_id, SIZE_GUIDE)
        pending[state_key] = state
        save_data(data)
        return

    if contains_any(text, PRICE_WORDS):
        send_state_reply(connection_id, chat_id, state, message_id, PRICE_REPLY)
        pending[state_key] = state
        save_data(data)
        return

    if stage == "awaiting_receipt":
        if contains_any(text, RECEIPT_WORDS):
            send_state_reply(connection_id, chat_id, state, message_id, RECEIPT_REMINDERS[0])
        pending[state_key] = state
        save_data(data)
        return

    if stage == "available" and is_order_request(text):
        combined = ORDER_FORM + "\n\n" + data.get("payment_message", DEFAULT_PAYMENT_MESSAGE)
        payment_msg = send_state_reply(connection_id, chat_id, state, message_id, combined)
        if payment_msg:
            data.setdefault("payment_messages", []).append({
                "business_connection_id": connection_id,
                "chat_id": chat_id,
                "message_id": payment_msg.get("message_id"),
            })
            state["step"] = "awaiting_receipt"
        pending[state_key] = state
        save_data(data)
        return

    # Unknown messages intentionally receive no reply.
    pending[state_key] = state
    save_data(data)


def handle_admin_message(msg: Dict[str, Any]) -> None:
    user_id = (msg.get("from") or {}).get("id")
    if user_id != ADMIN_ID:
        return

    data = load_data()
    text_raw = msg.get("text") or ""
    text = normalize(text_raw)

    if data.get("awaiting_payment_edit") and text_raw:
        data["payment_message"] = text_raw
        data["awaiting_payment_edit"] = False
        save_data(data)
        send_admin("✅ پیام ۲ با موفقیت جایگزین شد.", admin_keyboard())
        return

    if text in ("/start", "/panel"):
        send_admin("پنل مدیریت ربات 👇", admin_keyboard())
    else:
        send_admin("برای مدیریت از /panel استفاده کن.", admin_keyboard())


def delete_all_payment_messages() -> str:
    data = load_data()
    items = data.get("payment_messages", [])
    groups: Dict[tuple, List[int]] = {}
    for item in items:
        cid = item.get("business_connection_id")
        chat_id = item.get("chat_id")
        mid = item.get("message_id")
        if cid and chat_id is not None and mid:
            groups.setdefault((cid, chat_id), []).append(int(mid))

    deleted = 0
    failed = 0
    remaining: List[Dict[str, Any]] = []

    for (cid, chat_id), mids in groups.items():
        for i in range(0, len(mids), 100):
            batch = mids[i:i + 100]
            try:
                api("deleteBusinessMessages", {
                    "business_connection_id": cid,
                    "message_ids": batch,
                })
                deleted += len(batch)
            except Exception:
                failed += len(batch)
                for mid in batch:
                    remaining.append({
                        "business_connection_id": cid,
                        "chat_id": chat_id,
                        "message_id": mid,
                    })

    data["payment_messages"] = remaining
    save_data(data)
    result = f"✅ {deleted} پیام شماره کارت حذف شد."
    if failed:
        result += f"\n⚠️ {failed} پیام حذف نشد؛ مجوز حذف پیام‌های ارسالی را در Telegram Business بررسی کن."
    return result


def handle_callback(cb: Dict[str, Any]) -> None:
    try:
        api("answerCallbackQuery", {"callback_query_id": cb["id"]})
    except Exception:
        pass

    if (cb.get("from") or {}).get("id") != ADMIN_ID:
        return

    action = cb.get("data")
    data = load_data()
    if action == "edit_payment":
        data["awaiting_payment_edit"] = True
        save_data(data)
        send_admin("پیام جدید بخش ۲ را همینجا به صورت متن بفرست.")
    elif action == "show_payment":
        send_admin(data.get("payment_message", DEFAULT_PAYMENT_MESSAGE))
    elif action == "delete_payment":
        send_admin(delete_all_payment_messages(), admin_keyboard())


def process_update(update: Dict[str, Any]) -> None:
    if update.get("business_connection"):
        handle_business_connection(update["business_connection"])
    elif update.get("business_message"):
        handle_business_message(update["business_message"])
    elif update.get("message"):
        handle_admin_message(update["message"])
    elif update.get("callback_query"):
        handle_callback(update["callback_query"])


def main() -> None:
    if BOT_TOKEN == "PUT_BOT_TOKEN_HERE":
        raise RuntimeError("BOT_TOKEN را در Environment Variables تنظیم کنید.")
    if ADMIN_ID == 0:
        raise RuntimeError("ADMIN_ID را در Environment Variables تنظیم کنید.")

    offset = None
    print("Boutique Telegram Business bot started...")
    while True:
        try:
            process_due_availability_replies()
        except Exception as e:
            print("DELAYED REPLY ERROR:", repr(e))
        payload: Dict[str, Any] = {
            "timeout": 5,
            "allowed_updates": ["message", "callback_query", "business_connection", "business_message"],
        }
        if offset is not None:
            payload["offset"] = offset
        try:
            updates = api("getUpdates", payload, timeout=60)
            # Collect every item of a Telegram photo album before processing it.
            # This makes a 10-photo album one customer turn and preserves all photos.
            media_groups: Dict[tuple, List[Dict[str, Any]]] = {}
            for update in updates:
                business_msg = update.get("business_message") or {}
                group_id = business_msg.get("media_group_id")
                if group_id:
                    group_key = (
                        business_msg.get("business_connection_id"),
                        (business_msg.get("chat") or {}).get("id"),
                        group_id,
                    )
                    media_groups.setdefault(group_key, []).append(business_msg)

            processed_groups = set()
            for update in updates:
                offset = update["update_id"] + 1
                try:
                    business_msg = update.get("business_message") or {}
                    group_id = business_msg.get("media_group_id")
                    if group_id:
                        group_key = (
                            business_msg.get("business_connection_id"),
                            (business_msg.get("chat") or {}).get("id"),
                            group_id,
                        )
                        if group_key not in processed_groups:
                            handle_business_message(business_msg, media_groups.get(group_key))
                            processed_groups.add(group_key)
                    else:
                        process_update(update)
                except Exception as e:
                    print("UPDATE ERROR:", repr(e), update.get("update_id"))
            process_due_availability_replies()
        except Exception as e:
            print("POLL ERROR:", repr(e))
            time.sleep(3)


if __name__ == "__main__":
    main()
