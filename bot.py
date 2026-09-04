import os
import json
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
AVAILABLE_REPLY = "سلام 🌹 بله تمامی محصولات ما موجوده ✅"
PHOTO_START_REPLY = "عکسی که فرستادی توی سفارشت ثبت شد ✅ بریم واسه ادامه سفارش"

SIZE_WORDS = [
    "سایز", "سايز", "سایض", "سایذ", "سایس", "سایژ", "سایظ", "سایزبندی", "سایز بندی",
    "راهنمای سایز", "راهنما سایز", "جدول سایز", "جدول سایزبندی", "اندازه", "سایزم", "سایزش",
    "چه سایزی", "چه سایز", "سایزم چیه", "سایزش چیه", "سایز مناسب", "اندازه مناسب", "فیت",
    "تن خور", "تنخور", "دور سینه", "عرض سینه", "قد کار", "دور کمر", "عرض کمر", "سرشانه",
    "xl", "xxl", "2xl", "3xl", "4xl", "اسمال", "مدیوم", "لارج", "اکس لارج", "ایکس لارج",
    "size", "sizing"
]
PRICE_WORDS = ["قیمت", "قيمت", "قیمط", "قیمتش", "چنده", "price"]


def default_data() -> Dict[str, Any]:
    return {
        "payment_message": DEFAULT_PAYMENT_MESSAGE,
        "payment_messages": [],
        "awaiting_payment_edit": False,
        "business_connections": {},
        "pending_order": {}
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


def handle_business_message(msg: Dict[str, Any]) -> None:
    data = load_data()
    if is_business_owner_message(msg, data):
        return

    connection_id = msg.get("business_connection_id")
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    if not connection_id or chat_id is None:
        return

    # Voice/audio -> only ask for typed text.
    if msg.get("voice") or msg.get("audio"):
        send_business(connection_id, chat_id, VOICE_REPLY)
        return

    # Track the conversation stage per business chat.
    state_key = f"{connection_id}:{chat_id}"
    pending = data.setdefault("pending_order", {})
    stage = pending.get(state_key)

    # A product photo at the beginning is treated as the selected item, not a receipt.
    # After payment details have been sent, an image/document is treated as a receipt.
    if msg.get("photo") or msg.get("document"):
        if stage == "awaiting_receipt":
            if forward_receipt_to_admin(msg):
                send_business(connection_id, chat_id, FINAL_MESSAGE)
            return

        send_business(connection_id, chat_id, PHOTO_START_REPLY)
        pending[state_key] = True
        save_data(data)
        return

    text = normalize(msg.get("text") or msg.get("caption") or "")
    if not text:
        return

    # Size questions get only size guide, with no forced order step.
    if is_size_request(text):
        send_business(connection_id, chat_id, SIZE_GUIDE)
        return

    # Price questions get only the fixed price answer.
    if contains_any(text, PRICE_WORDS):
        send_business(connection_id, chat_id, PRICE_REPLY)
        return

    # User requirement: first answer availability. The next ordinary customer text
    # triggers the three order messages. This state is per business chat.
    if not stage or stage == "awaiting_receipt":
        send_business(connection_id, chat_id, AVAILABLE_REPLY)
        pending[state_key] = True
        save_data(data)
        return

    # Next text after availability (or after a starting product photo) => send all three messages.
    send_business(connection_id, chat_id, ORDER_FORM)
    payment_msg = send_business(connection_id, chat_id, data.get("payment_message", DEFAULT_PAYMENT_MESSAGE))
    send_business(connection_id, chat_id, FINAL_MESSAGE)

    data.setdefault("payment_messages", []).append({
        "business_connection_id": connection_id,
        "chat_id": chat_id,
        "message_id": payment_msg.get("message_id"),
    })
    pending[state_key] = "awaiting_receipt"
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
        payload: Dict[str, Any] = {
            "timeout": 50,
            "allowed_updates": ["message", "callback_query", "business_connection", "business_message"],
        }
        if offset is not None:
            payload["offset"] = offset
        try:
            updates = api("getUpdates", payload, timeout=60)
            for update in updates:
                offset = update["update_id"] + 1
                try:
                    process_update(update)
                except Exception as e:
                    print("UPDATE ERROR:", repr(e), update.get("update_id"))
        except Exception as e:
            print("POLL ERROR:", repr(e))
            time.sleep(3)


if __name__ == "__main__":
    main()
