import os
import re
import json
import time
import random
import sqlite3
import requests
from datetime import datetime

TOKEN = os.environ["BOT_TOKEN"].strip()
ADMIN_ID = int(os.environ["ADMIN_ID"]) if os.environ.get("ADMIN_ID") else 0
API = f"https://api.telegram.org/bot{TOKEN}"
DB_PATH = os.environ.get("DB_PATH", "shop.db")

PRICE_MIN = 799_000
PRICE_MAX = 2_000_000
SHIPPING_FEE = 112_000

GREETINGS = [
    "سلام 👋 خوش اومدی 🌹 بگو دنبال چه لباسی هستی تا راهنماییت کنم.",
    "سلام عزیز 👋 خوش اومدی. اسم یا عکس محصول رو بفرست تا باهم بررسیش کنیم.",
    "سلام 🌹 در خدمتم. محصول، سایز یا قیمت هرچی خواستی بپرس."
]

PRICE_INTROS = [
    "برای این مدل، قیمت حدودی فعلی",
    "حدود قیمت این کار الان",
    "قیمت تقریبی این مدل در حال حاضر"
]

PRICE_DIFF_REPLIES = [
    "قیمت‌ها ممکنه به‌روزرسانی شده باشن و با قیمت قدیمی پیج فرق داشته باشن. برای قیمت قطعی همینجا تأیید می‌کنم 🌹",
    "بعضی پست‌های پیج با قیمت قبلی مونده‌ان. قیمت‌ها ممکنه تغییر کرده باشن؛ قبل از پرداخت قیمت قطعی رو تأیید می‌کنم.",
    "قیمت پیج ممکنه مربوط به قبل باشه. موجودی و قیمت‌ها تغییر می‌کنن؛ برای خرید، مبلغ نهایی رو همینجا قطعی می‌کنم 👌"
]

SHIPPING_METHOD_REPLIES = [
    "ارسال ما فقط با پست پیشتاز انجام می‌شه 📦 تیپاکس، باربری، اتوبوس و روش‌های دیگه نداریم.",
    "برای همه سفارش‌ها فقط پست پیشتاز داریم 🌹 امکان ارسال با تیپاکس، باربری یا اتوبوس نداریم.",
    "روش ارسال فروشگاه فقط پست پیشتازه 📮 برای نظم سفارش‌ها از روش‌های دیگه ارسال نمی‌کنیم."
]

SHIPPING_COST_REPLIES = [
    "هزینه ارسال کل سفارش فقط ۱۱۲٬۰۰۰ تومنه؛ فرقی نمی‌کنه ۱ محصول باشه یا تا سقف ۵۰ محصول 📦",
    "پست کل سفارش ۱۱۲ هزار تومنه ✅ برای سفارش‌های ۱ تا ۵۰ عدد همین یک هزینه ثابت حساب می‌شه.",
    "هزینه پست ثابت داریم: ۱۱۲٬۰۰۰ تومان برای کل سبد سفارش، نه برای هر محصول 🌹"
]

SHIPPING_CHEAP_REPLIES = [
    "چون حجم ارسال‌های روزانه‌مون بالاست، هزینه ارسال رو به‌صورت تجمیعی مدیریت می‌کنیم و برای مشتری فقط ۱۱۲ هزار تومان حساب می‌شه 📦",
    "به خاطر تعداد بالای مرسوله‌های روزانه، هزینه ارسال برای مشتری‌ها ثابت و اقتصادی در نظر گرفته شده؛ کل سفارش فقط ۱۱۲ هزار تومان.",
    "ارسال‌هامون روزانه و پرتعداده، برای همین هزینه پست رو ثابت نگه داشتیم تا مشتری مجبور نباشه بابت هر محصول جدا هزینه بده 🌹"
]

SHIPPING_TIME_REPLIES = [
    "ثبت و تحویل سفارش به پست معمولاً حدود ۳ تا ۵ روز کاری زمان می‌بره و مرسوله معمولاً حدود ۸ تا ۱۲ روز به دستتون می‌رسه 📦",
    "زمان آماده‌سازی و ارسال حدود ۳ تا ۵ روز کاریه؛ بعد از اون، رسیدن بسته معمولاً در بازه ۸ تا ۱۲ روز انجام می‌شه.",
    "سفارش‌ها معمولاً طی ۳ تا ۵ روز کاری وارد فرایند ارسال می‌شن و زمان رسیدن مرسوله معمولاً حدود ۸ تا ۱۲ روزه 🌹"
]

SHIPPING_DAYS_REPLIES = [
    "ارسال‌ها از شنبه تا پنجشنبه انجام می‌شن؛ جمعه ارسال نداریم 📦",
    "روزهای ارسال فروشگاه شنبه تا پنجشنبه‌ست و جمعه مرسوله‌ای تحویل پست نمی‌شه.",
    "مرسوله‌ها شنبه تا پنجشنبه ارسال می‌شن 🌹 جمعه ارسال نداریم."
]

LATE_DELIVERY_REPLIES = [
    "صبور باشین لطفاً 🌹 سفارش ارسال شده؛ به خاطر تعداد بالای مرسوله‌ها ثبت یا نمایش کد رهگیری بعضی وقت‌ها با تأخیر انجام می‌شه. جای نگرانی نیست.",
    "نگران نباشین 📦 مرسوله در فرایند ارساله. بعضی وقت‌ها به دلیل حجم بالای ارسال‌ها، ثبت کد رهگیری کمی دیرتر انجام می‌شه.",
    "سفارشتون در مسیر ارسال قرار گرفته 🌹 به خاطر تعداد زیاد مرسوله‌ها ممکنه ثبت کد ارسالی با تأخیر باشه؛ لطفاً کمی زمان بدین."
]

LOW_PRICE_REPLIES = [
    "قیمت‌گذاری ما بر اساس موجودی، حجم فروش و حاشیه سود پایین انجام می‌شه؛ برای همین بعضی مدل‌ها ممکنه از قیمت معمول بازار پایین‌تر باشن 🌹",
    "بعضی محصولات رو با حاشیه سود کمتر و فروش مستقیم عرضه می‌کنیم، برای همین قیمت‌ها اقتصادی‌تر درمیاد. مشخصات هر محصول رو قبل از خرید می‌تونیم تأیید کنیم 👌",
    "قیمت‌ها بسته به موجودی و شرایط تأمین تغییر می‌کنن و سعی می‌کنیم تا جای ممکن اقتصادی قیمت‌گذاری کنیم. برای هر محصول هم می‌تونی جزئیاتش رو جدا بپرسی 🌹"
]

UNKNOWN_REPLIES = [
    "متوجه منظورت نشدم 😅 یه جور دیگه برام بنویس تا دقیق راهنماییت کنم.",
    "یکم واضح‌تر می‌گی لطفاً؟ 🌹 می‌خوام درست متوجه سوالت بشم.",
    "منظورت رو کامل نگرفتم؛ اگه می‌شه کوتاه‌تر یا با کلمات دیگه بگو 👌",
    "این پیام رو دقیق متوجه نشدم. دوباره یه مدل دیگه بیانش کن تا کمکت کنم 🌹"
]

ORDER_TRIGGERS = ["سفارش", "میخوام", "می‌خوام", "خرید", "ثبت سفارش", "بخرم"]
PRICE_WORDS = ["قیمت", "چنده", "چند", "تومن", "تومان"]
SIZE_WORDS = ["سایز", "اندازه", "فیت", "قد", "وزن"]
PAY_WORDS = ["کارت", "پرداخت", "واریز", "شماره کارت"]
PRICE_DIFF_WORDS = ["پیج", "فرق", "متفاوت", "گرون", "ارزون", "قیمت داخل"]
SHIPPING_METHOD_WORDS = ["تیپاکس", "باربری", "اتوبوس", "ترمینال", "پیک", "چاپار"]
SHIPPING_COST_WORDS = ["هزینه ارسال", "هزینه پست", "پست چنده", "ارسال چنده", "کرایه"]
SHIPPING_CHEAP_WORDS = ["چرا ارسال پایینه", "چرا پست ارزونه", "چرا هزینه ارسال کمه", "چرا هزینه پست کمه"]
SHIPPING_TIME_WORDS = ["چند روزه", "کی میرسه", "کی می‌رسه", "زمان ارسال", "چقدر طول میکشه", "چقدر طول می‌کشه"]
SHIPPING_DAYS_WORDS = ["چه روز", "روزهای ارسال", "جمعه ارسال", "کی ارسال میکنید", "کی ارسال می‌کنید"]
LATE_WORDS = ["هنوز نرسیده", "چرا نرسیده", "به دستم نرسیده", "کد رهگیری", "کد ارسالی", "ارسال نکردید", "ارسال نکردین"]
LOW_PRICE_WORDS = ["چرا قیمتاتون پایینه", "چرا قیمت پایین", "چرا ارزونه", "چرا ارزون", "قیمتاتون چرا کمه"]

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chats(
            chat_id INTEGER PRIMARY KEY,
            connection_id TEXT,
            state TEXT DEFAULT '',
            product TEXT DEFAULT '',
            size TEXT DEFAULT '',
            full_name TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            address TEXT DEFAULT '',
            paused INTEGER DEFAULT 0,
            last_price INTEGER DEFAULT 0,
            expected_items INTEGER DEFAULT 0,
            collected_items INTEGER DEFAULT 0,
            misunderstood_count INTEGER DEFAULT 0
        )
    """)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(chats)").fetchall()}
    if "expected_items" not in cols:
        conn.execute("ALTER TABLE chats ADD COLUMN expected_items INTEGER DEFAULT 0")
    if "collected_items" not in cols:
        conn.execute("ALTER TABLE chats ADD COLUMN collected_items INTEGER DEFAULT 0")
    if "misunderstood_count" not in cols:
        conn.execute("ALTER TABLE chats ADD COLUMN misunderstood_count INTEGER DEFAULT 0")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS cart_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            price INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1
        )
    """)
    cart_cols = {row[1] for row in conn.execute("PRAGMA table_info(cart_items)").fetchall()}
    if "quantity" not in cart_cols:
        conn.execute("ALTER TABLE cart_items ADD COLUMN quantity INTEGER DEFAULT 1")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS product_price_history(
            chat_id INTEGER NOT NULL,
            normalized_name TEXT NOT NULL,
            display_name TEXT NOT NULL,
            price INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY(chat_id, normalized_name)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            product TEXT,
            size TEXT,
            full_name TEXT,
            phone TEXT,
            address TEXT,
            price INTEGER DEFAULT 0,
            receipt_file_id TEXT,
            status TEXT DEFAULT 'awaiting_receipt',
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS order_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            price INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1
        )
    """)
    order_cols = {row[1] for row in conn.execute("PRAGMA table_info(order_items)").fetchall()}
    if "quantity" not in order_cols:
        conn.execute("ALTER TABLE order_items ADD COLUMN quantity INTEGER DEFAULT 1")
    conn.commit()
    conn.close()


def api(method, data=None):
    r = requests.post(f"{API}/{method}", data=data or {}, timeout=65)
    r.raise_for_status()
    payload = r.json()
    if not payload.get("ok"):
        raise RuntimeError(payload)
    return payload["result"]

def send_business(connection_id, chat_id, text):
    return api("sendMessage", {
        "business_connection_id": connection_id,
        "chat_id": chat_id,
        "text": text
    })

def send_admin(text):
    if ADMIN_ID:
        return api("sendMessage", {"chat_id": ADMIN_ID, "text": text})

def send_admin_photo(file_id, caption):
    if ADMIN_ID:
        return api("sendPhoto", {
            "chat_id": ADMIN_ID,
            "photo": file_id,
            "caption": caption
        })

def get_setting(key, default=""):
    conn = db()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key, value):
    conn = db()
    conn.execute(
        "INSERT INTO settings(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value)
    )
    conn.commit()
    conn.close()

def get_chat(chat_id):
    conn = db()
    row = conn.execute("SELECT * FROM chats WHERE chat_id=?", (chat_id,)).fetchone()
    conn.close()
    return row

def ensure_chat(chat_id, connection_id):
    conn = db()
    conn.execute(
        "INSERT INTO chats(chat_id,connection_id) VALUES(?,?) "
        "ON CONFLICT(chat_id) DO UPDATE SET connection_id=excluded.connection_id",
        (chat_id, connection_id)
    )
    conn.commit()
    conn.close()

def update_chat(chat_id, **kwargs):
    if not kwargs:
        return
    conn = db()
    fields = ", ".join(f"{k}=?" for k in kwargs.keys())
    vals = list(kwargs.values()) + [chat_id]
    conn.execute(f"UPDATE chats SET {fields} WHERE chat_id=?", vals)
    conn.commit()
    conn.close()

def fmt_price(n):
    return f"{n:,}".replace(",", "٬") + " تومان"

def random_price():
    n = random.randrange(PRICE_MIN // 10_000, PRICE_MAX // 10_000 + 1) * 10_000
    return min(max(n, PRICE_MIN), PRICE_MAX)


MAX_ITEMS_PER_ORDER = 50

def normalize_product_name(name):
    t = (name or "").strip().lower()
    t = t.replace("ي", "ی").replace("ك", "ک").replace("ۀ", "ه").replace("ة", "ه")
    t = re.sub(r"[^\w\s\u0600-\u06FF]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

def get_or_create_product_price(chat_id, product_name):
    normalized = normalize_product_name(product_name)
    if not normalized:
        return random_price()

    conn = db()
    row = conn.execute(
        "SELECT price FROM product_price_history WHERE chat_id=? AND normalized_name=?",
        (chat_id, normalized)
    ).fetchone()
    if row:
        price = int(row["price"])
        conn.close()
        return price

    price = random_price()
    conn.execute(
        "INSERT OR IGNORE INTO product_price_history(chat_id,normalized_name,display_name,price,created_at) "
        "VALUES(?,?,?,?,?)",
        (chat_id, normalized, product_name.strip(), price, datetime.now().isoformat(timespec="seconds"))
    )
    conn.commit()
    row = conn.execute(
        "SELECT price FROM product_price_history WHERE chat_id=? AND normalized_name=?",
        (chat_id, normalized)
    ).fetchone()
    conn.close()
    return int(row["price"])

def clear_cart(chat_id):
    conn = db()
    conn.execute("DELETE FROM cart_items WHERE chat_id=?", (chat_id,))
    conn.commit()
    conn.close()

def cart_items(chat_id):
    conn = db()
    rows = conn.execute(
        "SELECT position, product_name, price, COALESCE(quantity,1) AS quantity "
        "FROM cart_items WHERE chat_id=? ORDER BY position",
        (chat_id,)
    ).fetchall()
    conn.close()
    return rows

def cart_unit_count(chat_id):
    return sum(int(r["quantity"]) for r in cart_items(chat_id))

def add_cart_item(chat_id, product_name, quantity=1):
    quantity = max(1, int(quantity))
    current_units = cart_unit_count(chat_id)
    if current_units + quantity > MAX_ITEMS_PER_ORDER:
        return None

    rows = cart_items(chat_id)
    position = len(rows) + 1
    price = get_or_create_product_price(chat_id, product_name)

    conn = db()
    conn.execute(
        "INSERT INTO cart_items(chat_id,position,product_name,price,quantity) VALUES(?,?,?,?,?)",
        (chat_id, position, product_name.strip(), price, quantity)
    )
    conn.commit()
    conn.close()
    update_chat(chat_id, collected_items=position)
    return position, price, quantity

def cart_subtotal(chat_id):
    return sum(int(r["price"]) * int(r["quantity"]) for r in cart_items(chat_id))

def cart_total(chat_id):
    rows = cart_items(chat_id)
    if not rows:
        return 0
    return cart_subtotal(chat_id) + SHIPPING_FEE

def cart_summary(chat_id):
    rows = cart_items(chat_id)
    if not rows:
        return "سبد سفارش خالیه."
    lines = []
    for r in rows:
        qty = int(r["quantity"])
        unit = int(r["price"])
        line_total = qty * unit
        if qty == 1:
            lines.append(f"{r['position']}. {r['product_name']} — حدود {fmt_price(unit)}")
        else:
            lines.append(
                f"{r['position']}. {r['product_name']} × {qty}\\n"
                f"   هر عدد: حدود {fmt_price(unit)} | جمع: {fmt_price(line_total)}"
            )
    lines.append(f"\\n💰 جمع حدودی: {fmt_price(cart_total(chat_id))}")
    lines.append(f"📦 تعداد کل: {cart_unit_count(chat_id)} عدد")
    return "\\n".join(lines)

def parse_count(text):
    trans = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    cleaned = text.translate(trans)
    m = re.search(r"\d+", cleaned)
    return int(m.group()) if m else None

def parse_quantity_product(text):
    """Examples: '50 تا هودی اسپایدرمن', '۵ عدد دورس مشکی', '3 تا از هودی'."""
    trans = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    cleaned = text.translate(trans).strip()
    m = re.match(r"^\s*(\d+)\s*(?:تا|عدد|دونه|دانه)\s*(?:از\s+)?(.+?)\s*$", cleaned)
    if not m:
        return None, None
    qty = int(m.group(1))
    product = m.group(2).strip()
    if not product:
        return None, None
    return qty, product

def is_done_choice(text):
    t = text.strip().lower()
    done_words = [
        "همین", "همینا", "همین ها", "همین‌ها", "همیناست", "تموم", "تمام",
        "دیگه ندارم", "نه", "اوکی", "تایید", "تأیید", "بله"
    ]
    return any(w in t for w in done_words)

def is_add_choice(text):
    t = text.strip().lower()
    add_words = ["اضافه", "بیشتر", "بازم", "باز هم", "یکی دیگه", "محصول دیگه"]
    return any(w in t for w in add_words)


def payment_text():
    card = get_setting("card_number")
    holder = get_setting("card_holder")
    if not card or not holder:
        return "اطلاعات کارت هنوز توسط فروشگاه تنظیم نشده. یک لحظه صبر کن تا برات بررسی بشه 🌹"
    return (
        f"💳 شماره کارت:\n{card}\n\n"
        f"👤 به نام: {holder}\n\n"
        "بعد از واریز لطفاً عکس رسید رو همینجا بفرست 📸"
    )

def contains_any(text, words):
    t = text.lower()
    return any(w in t for w in words)

def extract_phone(text):
    digits = re.sub(r"\D", "", text)
    if 10 <= len(digits) <= 12:
        return digits
    return ""

def start_order(chat_id):
    clear_cart(chat_id)
    update_chat(
        chat_id,
        state="await_product_count",
        product="",
        size="",
        full_name="",
        phone="",
        address="",
        last_price=0,
        expected_items=0,
        collected_items=0,
        misunderstood_count=0
    )


def create_order(chat_id):
    c = get_chat(chat_id)
    items = cart_items(chat_id)
    total = sum(int(r["price"]) * int(r["quantity"]) for r in items) + (SHIPPING_FEE if items else 0)
    product_summary = " | ".join(
        f"{r['position']}. {r['product_name']} x{r['quantity']}" for r in items
    )
    conn = db()
    cur = conn.execute("""
        INSERT INTO orders(chat_id,product,size,full_name,phone,address,price,created_at)
        VALUES(?,?,?,?,?,?,?,?)
    """, (
        chat_id, product_summary, c["size"], c["full_name"],
        c["phone"], c["address"], total,
        datetime.now().isoformat(timespec="seconds")
    ))
    order_id = cur.lastrowid
    for r in items:
        conn.execute(
            "INSERT INTO order_items(order_id,position,product_name,price,quantity) VALUES(?,?,?,?,?)",
            (order_id, r["position"], r["product_name"], r["price"], r["quantity"])
        )
    conn.commit()
    conn.close()
    update_chat(chat_id, product=product_summary, last_price=total)
    return order_id


def latest_waiting_order(chat_id):
    conn = db()
    row = conn.execute(
        "SELECT * FROM orders WHERE chat_id=? AND status='awaiting_receipt' "
        "ORDER BY id DESC LIMIT 1", (chat_id,)
    ).fetchone()
    conn.close()
    return row

def handle_admin_message(msg):
    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()

    if text == "/myid":
        api("sendMessage", {"chat_id": chat_id, "text": f"Telegram ID شما:\n{chat_id}"})
        return

    if not ADMIN_ID or chat_id != ADMIN_ID:
        if text.startswith("/"):
            api("sendMessage", {
                "chat_id": chat_id,
                "text": "این بخش فقط برای مدیر فروشگاه فعاله."
            })
        return

    if text.startswith("/setcard"):
        card = re.sub(r"\D", "", text.replace("/setcard", "", 1))
        if len(card) != 16:
            send_admin("فرمت درست:\n/setcard 6037991234567890")
            return
        set_setting("card_number", card)
        send_admin(f"✅ شماره کارت جدید ذخیره شد:\n{card}")
        return

    if text.startswith("/setholder"):
        holder = text.replace("/setholder", "", 1).strip()
        if not holder:
            send_admin("فرمت درست:\n/setholder نام و نام خانوادگی صاحب کارت")
            return
        set_setting("card_holder", holder)
        send_admin(f"✅ نام صاحب کارت ذخیره شد:\n{holder}")
        return

    if text == "/cardinfo":
        send_admin(payment_text())
        return

    if text == "/orders":
        conn = db()
        rows = conn.execute(
            "SELECT id,full_name,product,size,status,price FROM orders "
            "ORDER BY id DESC LIMIT 10"
        ).fetchall()
        conn.close()
        if not rows:
            send_admin("هنوز سفارشی ثبت نشده.")
            return
        out = ["🧾 ۱۰ سفارش آخر:"]
        for r in rows:
            out.append(
                f"\n#{r['id']} | {r['full_name'] or '-'}\n"
                f"{r['product'] or '-'} | سایز {r['size'] or '-'}\n"
                f"{fmt_price(r['price']) if r['price'] else 'قیمت ثبت نشده'} | {r['status']}"
            )
        send_admin("\n".join(out))
        return

    if text.startswith("/pause"):
        raw = re.sub(r"\D", "", text.replace("/pause", "", 1))
        if not raw:
            send_admin("فرمت: /pause CHAT_ID")
            return
        update_chat(int(raw), paused=1)
        send_admin(f"⏸ پاسخ خودکار برای چت {raw} متوقف شد.")
        return

    if text.startswith("/resume"):
        raw = re.sub(r"\D", "", text.replace("/resume", "", 1))
        if not raw:
            send_admin("فرمت: /resume CHAT_ID")
            return
        update_chat(int(raw), paused=0)
        send_admin(f"▶️ پاسخ خودکار برای چت {raw} فعال شد.")
        return

    if text.startswith("/resetprices"):
        raw = re.sub(r"\D", "", text.replace("/resetprices", "", 1))
        if not raw:
            send_admin("فرمت: /resetprices CHAT_ID")
            return
        conn = db()
        conn.execute("DELETE FROM product_price_history WHERE chat_id=?", (int(raw),))
        conn.commit()
        conn.close()
        send_admin(f"✅ قیمت‌های ذخیره‌شده برای مشتری {raw} پاک شد.")
        return

    if text == "/admin":
        send_admin(
            "⚙️ دستورات مدیریت:\n\n"
            "/setcard شماره‌کارت\n"
            "/setholder نام صاحب کارت\n"
            "/cardinfo\n"
            "/orders\n"
            "/pause CHAT_ID\n"
            "/resume CHAT_ID\n"
            "/resetprices CHAT_ID"
        )

def handle_business_message(msg, business_owner_id=0):
    connection_id = msg.get("business_connection_id")
    chat_id = msg["chat"]["id"]
    sender_id = (msg.get("from") or {}).get("id", 0)

    if business_owner_id and sender_id == business_owner_id:
        return
    if not connection_id:
        return

    ensure_chat(chat_id, connection_id)
    c = get_chat(chat_id)
    if c and c["paused"]:
        return

    text = (msg.get("text") or msg.get("caption") or "").strip()
    state = c["state"] if c else ""

    if msg.get("photo") and state != "await_receipt":
        if not state:
            start_order(chat_id)
        c = get_chat(chat_id)
        if c["state"] == "await_product_count":
            send_business(
                connection_id, chat_id,
                "عکس محصول رو گرفتم 👌 چند تا محصول می‌خوای سفارش بدی؟ "
                "فقط تعداد کل رو با عدد بفرست؛ از ۱ تا ۵۰. بعد اسم‌هاشون رو یکی‌یکی ازت می‌پرسم."
            )
        elif c["state"] == "await_item_name":
            current = int(c["collected_items"]) + 1
            total_needed = int(c["expected_items"])
            send_business(
                connection_id, chat_id,
                f"اسکرین‌شات رسید 👌 برای اینکه اشتباه نشه، اسم محصول شماره {current} از {total_needed} رو تایپ کن."
            )
        else:
            send_business(
                connection_id, chat_id,
                "عکس رو گرفتم 👌 مراحل سفارش رو با متن ادامه بده تا دقیق ثبتش کنم."
            )
        return

    if msg.get("photo") and state == "await_receipt":
        order = latest_waiting_order(chat_id)
        if order:
            file_id = msg["photo"][-1]["file_id"]
            conn = db()
            conn.execute(
                "UPDATE orders SET receipt_file_id=?, status='receipt_sent' WHERE id=?",
                (file_id, order["id"])
            )
            item_rows = conn.execute(
                "SELECT position,product_name,price,COALESCE(quantity,1) AS quantity FROM order_items WHERE order_id=? ORDER BY position",
                (order["id"],)
            ).fetchall()
            conn.commit()
            conn.close()

            send_business(
                connection_id, chat_id,
                f"✅ رسید سفارش #{order['id']} دریافت شد و برای بررسی فروشگاه فرستادم 🌹"
            )

            items_text = "\n".join(
                (
                    f"{r['position']}. {r['product_name']} × {r['quantity']} — "
                    f"{fmt_price(int(r['price']) * int(r['quantity']))}"
                )
                for r in item_rows
            )
            caption = (
                f"📸 رسید سفارش #{order['id']}\n\n"
                f"{items_text}\n\n"
                f"📏 سایزها: {order['size']}\n"
                f"👤 نام: {order['full_name']}\n"
                f"📱 موبایل: {order['phone']}\n"
                f"📍 آدرس: {order['address']}\n"
                f"💰 جمع حدودی ثبت‌شده: {fmt_price(order['price']) if order['price'] else '-'}\n"
                f"💬 Chat ID: {chat_id}"
            )
            send_admin_photo(file_id, caption)
            return

        send_business(connection_id, chat_id, "رسید رو گرفتم، ولی سفارش فعالی پیدا نکردم. دوباره بگو «ثبت سفارش».")
        return

    if not text:
        return

    if state == "await_product_count":
        qty, product = parse_quantity_product(text)
        if qty is not None and product:
            if qty < 1 or qty > MAX_ITEMS_PER_ORDER:
                send_business(connection_id, chat_id, "تعداد باید بین ۱ تا ۵۰ عدد باشه.")
                return
            clear_cart(chat_id)
            result = add_cart_item(chat_id, product, qty)
            if not result:
                send_business(connection_id, chat_id, "حداکثر ۵۰ عدد محصول در هر سفارش قابل ثبت هست.")
                return
            position, price, quantity = result
            update_chat(chat_id, expected_items=1, collected_items=1, state="confirm_cart")
            send_business(
                connection_id, chat_id,
                f"✅ {quantity} عدد {product}\n"
                f"💰 قیمت ثابت هر عدد برای این محصول: {fmt_price(price)}\n"
                f"💰 جمع این محصول: {fmt_price(price * quantity)}\n\n"
                + cart_summary(chat_id) +
                "\n\nهمین محصول رو می‌خوای یا محصول دیگه‌ای هم اضافه کنم؟ "
                "بنویس «همین‌ها» یا «اضافه»."
            )
            return

        count = parse_count(text)
        if count is None:
            send_business(
                connection_id, chat_id,
                "تعداد محصولات رو با عدد بفرست؛ مثلاً 3.\n"
                "اگه چند عدد از یک مدل می‌خوای می‌تونی بنویسی: «۵۰ تا هودی اسپایدرمن»."
            )
            return
        if count < 1:
            send_business(connection_id, chat_id, "تعداد باید حداقل ۱ محصول باشه.")
            return
        if count > MAX_ITEMS_PER_ORDER:
            send_business(connection_id, chat_id, "حداکثر می‌تونم ۵۰ محصول رو در یک سفارش ثبت کنم. یک عدد بین ۱ تا ۵۰ بفرست 🌹")
            return
        clear_cart(chat_id)
        update_chat(chat_id, expected_items=count, collected_items=0, state="await_item_name")
        send_business(
            connection_id, chat_id,
            f"عالی 👌 {count} محصول. اسم محصول شماره ۱ از {count} رو بفرست. "
            "اگه از همین مدل چند عدد می‌خوای، مثل «3 تا هودی مشکی» بنویس."
        )
        return

    if state == "await_item_name":
        c = get_chat(chat_id)
        if int(c["collected_items"]) >= MAX_ITEMS_PER_ORDER:
            update_chat(chat_id, state="confirm_cart", expected_items=MAX_ITEMS_PER_ORDER)
            send_business(
                connection_id, chat_id,
                "به سقف ۵۰ محصول رسیدیم ✅\n\n" + cart_summary(chat_id) +
                "\n\nاگه همین‌هاست بنویس «همین‌ها» تا ادامه ثبت سفارش رو انجام بدیم."
            )
            return

        qty, product = parse_quantity_product(text)
        if qty is None:
            qty, product = 1, text.strip()

        remaining_units = MAX_ITEMS_PER_ORDER - cart_unit_count(chat_id)
        if qty < 1 or qty > remaining_units:
            send_business(
                connection_id, chat_id,
                f"با سفارش فعلی حداکثر {remaining_units} عدد دیگه می‌تونی اضافه کنی."
            )
            return

        result = add_cart_item(chat_id, product, qty)
        if not result:
            send_business(connection_id, chat_id, "حداکثر ۵۰ عدد محصول در هر سفارش قابل ثبت هست.")
            return

        position, price, quantity = result
        c = get_chat(chat_id)
        expected = int(c["expected_items"])
        collected = int(c["collected_items"])

        reused = " (همون قیمت قبلی این محصول ✅)" if quantity >= 1 else ""
        if quantity == 1:
            item_text = (
                f"✅ محصول {position}: {product}\n"
                f"💰 قیمت حدودی ثابت: {fmt_price(price)}{reused}"
            )
        else:
            item_text = (
                f"✅ محصول {position}: {product} × {quantity}\n"
                f"💰 هر عدد: {fmt_price(price)}{reused}\n"
                f"💰 جمع این محصول: {fmt_price(price * quantity)}"
            )
        send_business(connection_id, chat_id, item_text)

        if collected < expected:
            send_business(
                connection_id, chat_id,
                f"حالا اسم محصول شماره {collected + 1} از {expected} رو بفرست."
            )
            return

        update_chat(chat_id, state="confirm_cart")
        send_business(
            connection_id, chat_id,
            "این محصولات ثبت شدن:\n\n" + cart_summary(chat_id) +
            "\n\nهمین محصولات رو می‌خوای یا محصول دیگه‌ای هم اضافه کنم؟ "
            "بنویس «همین‌ها» یا «اضافه»."
        )
        return

    if state == "confirm_cart":
        rows = cart_items(chat_id)
        current_count = cart_unit_count(chat_id)

        if is_add_choice(text):
            if current_count >= MAX_ITEMS_PER_ORDER:
                update_chat(chat_id, state="await_size")
                send_business(
                    connection_id, chat_id,
                    "به سقف ۵۰ محصول رسیدیم و امکان اضافه‌کردن بیشتر نیست.\n\n"
                    + cart_summary(chat_id) +
                    "\n\nحالا سایز هر محصول رو به ترتیب بنویس؛ مثلاً:\n1: L\n2: XL\n3: L"
                )
                return
            update_chat(chat_id, state="await_add_count")
            send_business(
                connection_id, chat_id,
                f"حتماً 👌 الان {current_count} محصول داری. چند محصول دیگه اضافه کنم؟ "
                f"حداکثر {MAX_ITEMS_PER_ORDER - current_count} تا."
            )
            return

        if is_done_choice(text):
            total = cart_total(chat_id)
            update_chat(chat_id, last_price=total, state="await_size")
            send_business(
                connection_id, chat_id,
                "باشه ✅ سفارش محصولاتت تا اینجا:\n\n" + cart_summary(chat_id) +
                "\n\nحالا سایز هر محصول رو به ترتیب بنویس؛ مثلاً:\n1: L\n2: XL\n3: L\n\n"
                "این قیمت‌ها حدودی هستن و قبل از پرداخت باید مبلغ نهایی تأیید بشه."
            )
            return

        send_business(
            connection_id, chat_id,
            "اگه همین محصولات رو می‌خوای بنویس «همین‌ها». "
            "اگه محصول دیگه هم داری بنویس «اضافه»."
        )
        return

    if state == "await_add_count":
        current_count = cart_unit_count(chat_id)
        remaining = MAX_ITEMS_PER_ORDER - current_count
        count = parse_count(text)
        if count is None:
            send_business(connection_id, chat_id, f"تعداد محصولات جدید رو با عدد بفرست؛ حداکثر {remaining}.")
            return
        if count < 1:
            send_business(connection_id, chat_id, "تعداد باید حداقل ۱ باشه.")
            return
        if count > remaining:
            send_business(
                connection_id, chat_id,
                f"با سفارش فعلی فقط {remaining} محصول دیگه می‌تونم اضافه کنم؛ سقف هر سفارش ۵۰ محصوله."
            )
            return
        existing_lines = len(cart_items(chat_id))
        new_expected = existing_lines + count
        update_chat(chat_id, expected_items=new_expected, collected_items=existing_lines, state="await_item_name")
        send_business(
            connection_id, chat_id,
            f"اوکی 👌 اسم محصول شماره {existing_lines + 1} از {new_expected} رو بفرست. "
            "اگر چند عدد از یک مدل می‌خوای، مثلاً بنویس «5 تا دورس مشکی»."
        )
        return

    if state == "await_size":
        update_chat(chat_id, size=text, state="await_name")
        send_business(connection_id, chat_id, "اسم و فامیلی تحویل‌گیرنده رو بفرست 🌹")
        return

    if state == "await_name":
        update_chat(chat_id, full_name=text, state="await_phone")
        send_business(connection_id, chat_id, "شماره موبایل رو بفرست؛ مثلاً 09123456789.")
        return

    if state == "await_phone":
        phone = extract_phone(text)
        if not phone:
            send_business(connection_id, chat_id, "شماره موبایل درست به نظر نمی‌رسه؛ دوباره بفرست لطفاً.")
            return
        update_chat(chat_id, phone=phone, state="await_address")
        send_business(connection_id, chat_id, "آدرس کامل ارسال رو بفرست؛ شهر، خیابون، پلاک و اگر داری کدپستی.")
        return

    if state == "await_address":
        update_chat(chat_id, address=text, state="await_receipt")
        order_id = create_order(chat_id)
        c = get_chat(chat_id)
        items_text = cart_summary(chat_id)
        summary = (
            f"✅ سفارش #{order_id} ثبت اولیه شد.\n\n"
            f"{items_text}\n\n"
            f"📏 سایزها: {c['size']}\n"
            f"👤 نام: {c['full_name']}\n"
            f"📱 موبایل: {c['phone']}\n"
            f"📍 آدرس: {c['address']}\n\n"
            "⚠️ جمع بالا حدودی است؛ قبل از پرداخت مبلغ نهایی باید توسط فروشگاه تأیید شود.\n\n"
            + payment_text()
        )
        send_business(connection_id, chat_id, summary)

        admin_items = "\n".join(
            f"{r['position']}. {r['product_name']} — {fmt_price(r['price'])}"
            for r in cart_items(chat_id)
        )
        send_admin(
            f"🆕 سفارش اولیه #{order_id}\n\n"
            f"{admin_items}\n\n"
            f"جمع حدودی: {fmt_price(c['last_price'])}\n"
            f"سایزها: {c['size']}\n"
            f"نام: {c['full_name']}\n"
            f"موبایل: {c['phone']}\n"
            f"آدرس: {c['address']}\n"
            f"Chat ID: {chat_id}\n\n"
            f"برای توقف پاسخ خودکار این چت:\n/pause {chat_id}"
        )
        return

    # Shipping and delivery questions
    low = text.lower()

    if contains_any(low, SHIPPING_CHEAP_WORDS):
        update_chat(chat_id, misunderstood_count=0)
        send_business(connection_id, chat_id, random.choice(SHIPPING_CHEAP_REPLIES))
        return

    if contains_any(low, SHIPPING_METHOD_WORDS):
        update_chat(chat_id, misunderstood_count=0)
        send_business(connection_id, chat_id, random.choice(SHIPPING_METHOD_REPLIES))
        return

    if contains_any(low, SHIPPING_COST_WORDS):
        update_chat(chat_id, misunderstood_count=0)
        send_business(connection_id, chat_id, random.choice(SHIPPING_COST_REPLIES))
        return

    if contains_any(low, LATE_WORDS):
        update_chat(chat_id, misunderstood_count=0)
        send_business(connection_id, chat_id, random.choice(LATE_DELIVERY_REPLIES))
        return

    if contains_any(low, SHIPPING_DAYS_WORDS):
        update_chat(chat_id, misunderstood_count=0)
        send_business(connection_id, chat_id, random.choice(SHIPPING_DAYS_REPLIES))
        return

    if contains_any(low, SHIPPING_TIME_WORDS):
        update_chat(chat_id, misunderstood_count=0)
        send_business(connection_id, chat_id, random.choice(SHIPPING_TIME_REPLIES))
        return

    if contains_any(low, LOW_PRICE_WORDS):
        update_chat(chat_id, misunderstood_count=0)
        send_business(connection_id, chat_id, random.choice(LOW_PRICE_REPLIES))
        return

    if contains_any(text, PRICE_DIFF_WORDS) and contains_any(text, PRICE_WORDS):
        send_business(connection_id, chat_id, random.choice(PRICE_DIFF_REPLIES))
        return

    if contains_any(text, ORDER_TRIGGERS):
        update_chat(chat_id, misunderstood_count=0)
        start_order(chat_id)
        send_business(
            connection_id, chat_id,
            "حتماً 🌹 چند تا محصول می‌خوای سفارش بدی؟ "
            "فقط تعداد رو با عدد بفرست؛ از ۱ تا ۵۰. بعد اسم هر محصول رو یکی‌یکی ازت می‌پرسم."
        )
        return

    if contains_any(text, PAY_WORDS):
        update_chat(chat_id, misunderstood_count=0)
        send_business(connection_id, chat_id, payment_text())
        return

    if contains_any(text, SIZE_WORDS):
        update_chat(chat_id, misunderstood_count=0)
        send_business(
            connection_id, chat_id,
            random.choice([
                "برای اینکه سایز دقیق‌تر بگم، قد و وزنت رو بفرست و بگو لباس رو جذب دوست داری یا آزاد 👌",
                "قد، وزن و مدل لباس رو بفرست؛ مثلاً «قد ۱۸۰، وزن ۸۰، هودی». بعد راهنماییت می‌کنم 🌹",
                "سایز رو با قد و وزن بهتر می‌تونم پیشنهاد بدم. قد و وزنت رو بفرست و بگو فیت آزاد می‌خوای یا معمولی."
            ])
        )
        return

    if contains_any(text, PRICE_WORDS):
        update_chat(chat_id, misunderstood_count=0)
        price = random_price()
        update_chat(chat_id, last_price=price)
        intro = random.choice(PRICE_INTROS)
        send_business(
            connection_id, chat_id,
            f"{intro} حدود {fmt_price(price)} هست 🌹\n"
            "این مبلغ تقریبیه؛ قبل از پرداخت قیمت قطعی رو تأیید می‌کنم."
        )
        return

    if text.lower() in ["سلام", "سلامم", "hi", "hello", "درود"]:
        update_chat(chat_id, misunderstood_count=0)
        send_business(connection_id, chat_id, random.choice(GREETINGS))
        return

    c = get_chat(chat_id)
    miss = int(c["misunderstood_count"] or 0) + 1
    if miss >= 3:
        update_chat(chat_id, misunderstood_count=0)
        send_business(connection_id, chat_id, "بله درسته ✅")
    else:
        update_chat(chat_id, misunderstood_count=miss)
        send_business(connection_id, chat_id, random.choice(UNKNOWN_REPLIES))


def main():
    init_db()
    offset = 0
    business_owner_id = int(get_setting("business_owner_id", "0") or "0")
    print("Telegram Business Shop Bot v2 is running...", flush=True)

    while True:
        try:
            updates = api("getUpdates", {
                "offset": offset,
                "timeout": 50,
                "allowed_updates": json.dumps([
                    "business_connection",
                    "business_message",
                    "message"
                ])
            })

            for update in updates:
                offset = update["update_id"] + 1

                if "business_connection" in update:
                    bc = update["business_connection"]
                    user = bc.get("user") or {}
                    uid = user.get("id")
                    if uid:
                        business_owner_id = int(uid)
                        set_setting("business_owner_id", str(uid))
                    print(
                        f"Business connection: id={bc.get('id')} "
                        f"enabled={bc.get('is_enabled')} owner={uid}",
                        flush=True
                    )

                if "message" in update:
                    handle_admin_message(update["message"])

                if "business_message" in update:
                    handle_business_message(
                        update["business_message"],
                        business_owner_id=business_owner_id
                    )

        except requests.RequestException as e:
            print("Network error:", repr(e), flush=True)
            time.sleep(5)
        except Exception as e:
            print("Error:", repr(e), flush=True)
            time.sleep(5)

if __name__ == "__main__":
    main()