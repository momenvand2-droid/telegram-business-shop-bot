import json
import logging
import os
import re
import sqlite3
import time
from typing import Dict, Any, Optional

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

# ----- Logging -----
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ----- Conversation states -----
NAME, ADDRESS, POSTAL_CODE, PHONE, PRODUCT_PHOTO, PRICE_AWARE, SIZE, CONFIRM_PAYMENT = range(8)

# ----- Storage -----
DATA_FILE = "orders.json"  # JSON store for order data (non-image)
DEFAULT_CARD = "1234-5678-9012-3456"
orders: Dict[int, Dict[str, Any]] = {}
card_info: Dict[str, str] = {"current_card": DEFAULT_CARD}

# SQLite DB for images and editable texts
DB_FILE = "orders.db"

def db_init():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS product_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            file_id TEXT,
            created_at INTEGER
        );
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS sent_card_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            business_connection_id TEXT,
            created_at INTEGER
        );
        """
    )
    # defaults
    defaults = {
        "welcome_text": (
            "سلام مشتری عزیز {username}❤️\n"
            "به ربات ثبت سفارش فروشگاه اینترنتی بوتیک‌ما خوش آمدید😍🛍️\n"
            "تمامی محصولاتی که در پیج وجود داره (استوری،هایلایت،پست،ریلز) موجود هستن🌹\n"
            "ثبت سفارشتون رو شروع می‌کنیم؛ لطفاً اطلاعات خواسته‌شده رو مرحله‌به‌مرحله ارسال کنید👇🏻"
        ),
        "prepay_text": (
            "🛑 نکات مهم قبل از پرداخت:\n\n"
            "✅ بعد از واریز، لطفاً رسید پرداخت رو برامون ارسال کنید تا سفارشتون رو ثبت کنیم. 🧾 (لطفاً رسید رو از گالری گوشیتون بفرستید.)\n\n"
            "🚚 ارسال سفارش شما بین 3 تا 5 روز کاری زمان می‌بره. اگر امروز واریز کنید، معمولاً فردا ارسال میشه و طبق زمان‌بندی اعلام شده به دستتون می‌رسه. ⏳\n\n"
            "📦 کد رهگیری مرسوله از طریق پیامک براتون ارسال میشه و همچنین در استوری‌هامون هم اطلاع‌رسانی می‌کنیم. 📲✨"
        ),
        "success_text": (
            "✨ ممنونم بابت واریزی مشتری عزیز! ✨\n\n"
            "از خرید و اعتمادتون به فروشگاه بوتیک‌ما بی‌نهایت سپاسگزاریم! 🙏🏻💖\n\n"
            "خوشحالیم به اطلاعتون برسونیم که لباس زیبای شما که سفارش دادید، فردا ارسال خواهد شد و به زودی به دستتون می‌رسه. 🚚🎁\n\n"
            "امیدواریم از خریدتون لذت ببرید و محصول ما براتون خوش‌یمن باشه. 🍀\n\n"
            "خداوند به روزی شما برکت بده! 🤲🏻💰"
        ),
        "support_id": "@TachiVaNa_admin",

        # NEW: card message + owner
        "card_owner": "صحرا",
        "card_text": (
            "💰 مبلغ درج شده در کپشن به علاوه 50 هزار تومان هزینه ارسال واریز کنید به مشخصات زیر:\n"
            "💳 {card_number}\n"
            "👤به نام: {owner_name}\n"
            "🚚هرچند تا محصول که میخوایید انتخاب کنید و پول یدونه ارسال بدید لازم نیست برای هر محصول مبلغ جدا گونه برای ارسال واریز کنید.\n"
            "🎙اگه اپلیکیشن آپ بهتون خطا داد از همراه بانک یا ATM و یا اپلیکیشن های واریز دیگه مثل دیجی پی یا تاپ و... استفاده کنید."
        ),
    }
    for k, v in defaults.items():
        c.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))
    conn.commit()
    conn.close()

def db_get_setting(key: str) -> str:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else ""

def db_set_setting(key: str, value: str) -> None:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("REPLACE INTO settings(key,value) VALUES(?,?)", (key, value))
    conn.commit()
    conn.close()

def db_store_photo(user_id: int, file_id: str) -> None:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO product_images(user_id, file_id, created_at) VALUES(?,?,?)",
        (user_id, file_id, int(time.time())),
    )
    conn.commit()
    conn.close()

def db_delete_all_images() -> None:
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("DELETE FROM product_images")
        conn.commit()
        conn.close()
    except Exception:
        logger.exception("Failed to delete all product images")


def db_store_card_message(chat_id: int, message_id: int, business_connection_id: str | None) -> None:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO sent_card_messages(chat_id,message_id,business_connection_id,created_at) VALUES(?,?,?,?)",
        (chat_id, message_id, business_connection_id, int(time.time())),
    )
    conn.commit()
    conn.close()

def db_get_card_messages():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id,chat_id,message_id,business_connection_id FROM sent_card_messages ORDER BY id")
    rows = c.fetchall()
    conn.close()
    return rows

def db_delete_card_message_record(row_id: int) -> None:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM sent_card_messages WHERE id=?", (row_id,))
    conn.commit()
    conn.close()


# ----- Data JSON helpers (non-image) -----
def load_data() -> None:
    global orders, card_info
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        orders = data.get("orders", {})
        card_info = data.get("card_info", {"current_card": DEFAULT_CARD})
    except Exception:
        orders = {}
        card_info = {"current_card": DEFAULT_CARD}

def save_data() -> None:
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"orders": orders, "card_info": card_info}, f, ensure_ascii=False, indent=2)
    except Exception:
        logger.exception("Failed to write data file")


# ----- Admins -----
raw_admins = os.getenv("ADMIN_IDS", "293380958,1027791230").strip()     #raw_admins = os.getenv("ADMIN_IDS", "admine 1,admine 2, ...").strip()
ADMIN_IDS = {int(x) for x in raw_admins.split(",") if x.strip().isdigit()}

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ----- Sizing rules -----
# "قد 190 تا 2" interpreted as 190 to 200 cm
RANGES = [
    ("S", (40, 50), (150, 160)),
    ("M", (50, 60), (160, 170)),
    ("L", (60, 80), (170, 180)),
    ("XL", (80, 90), (180, 190)),
    ("XXL", (90, 100), (190, 200)),
    ("XXXL", (100, 110), (190, 200)),
    ("XXXXL", (110, 120), (190, 200)),
]

def estimate_size(height: int, weight: int) -> str:
    for label, (w_min, w_max), (h_min, h_max) in RANGES:
        if w_min <= weight <= w_max and h_min <= height <= h_max:
            return label
    # fallback heuristic if out of bands
    if weight < 50 or height < 160:
        return "S"
    if weight < 60 or height < 170:
        return "M"
    if weight < 80 or height < 180:
        return "L"
    if weight < 90 or height < 190:
        return "XL"
    if weight < 100:
        return "XXL"
    if weight < 110:
        return "XXXL"
    return "XXXXL"


# ----- Helpers -----
def get_last_product_photo(user_id: int) -> Optional[str]:
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute(
            "SELECT file_id FROM product_images WHERE user_id=? ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        )
        row = c.fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None


# ----- Handlers -----
async def business_first_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the order flow from the customer's first Telegram Business message.

    No /start command or start button is required in a connected Business chat.
    Message.reply_text automatically keeps the message business_connection_id
    in python-telegram-bot 21.1+, so replies are sent on behalf of the connected
    business account.
    """
    msg = update.business_message or update.effective_message
    user = update.effective_user

    if not msg or not user:
        return ConversationHandler.END

    # Ignore messages generated by a bot itself to avoid reply loops.
    if getattr(msg, "sender_business_bot", None) or getattr(user, "is_bot", False):
        return ConversationHandler.END

    # Ignore outgoing/manual messages sent by the owner of the connected Business account.
    # This lookup also makes the protection work after a process restart.
    business_connection_id = getattr(msg, "business_connection_id", None)
    if business_connection_id:
        try:
            connection = await context.bot.get_business_connection(business_connection_id)
            if connection and connection.user and user.id == connection.user.id:
                return ConversationHandler.END
            if connection and not connection.is_enabled:
                logger.info("Ignoring disabled business connection %s", business_connection_id)
                return ConversationHandler.END
        except Exception:
            logger.exception("Could not verify business connection %s", business_connection_id)

    # Admins keep using their normal bot chat/panel instead of entering customer flow.
    if is_admin(user.id):
        return ConversationHandler.END

    # A fresh business conversation starts a fresh order state.
    context.user_data.clear()
    context.user_data["business_connection_id"] = business_connection_id

    welcome = db_get_setting("welcome_text").format(
        username=user.first_name or user.username or "کاربر"
    )
    # Backward-compatible cleanup if an existing DB still contains the old / button wording.
    welcome = welcome.replace(
        "برای شروع ثبت سفارش از دکمه ثبت سفارش استفاده کنید👇🏻",
        "ثبت سفارشتون رو شروع می‌کنیم؛ لطفاً اطلاعات خواسته‌شده رو مرحله‌به‌مرحله ارسال کنید👇🏻",
    )
    await msg.reply_text(welcome)
    await msg.reply_text("لطفاً نام و نام خانوادگی خودتون رو وارد کنید: (لطفاً با دقت وارد کنید!)")
    return NAME


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    # debuge user/admin
#    dbg = (
#        f"Admins: {sorted(ADMIN_IDS)}\n"
#        f"Your Telegram user_id: {user.id}\n"
#        f"Admin? {'YES ✅' if is_admin(user.id) else 'NO ❌'}"
#    )
#    print(dbg)
#    await update.effective_message.reply_text(dbg)

    if is_admin(user.id):
        await send_admin_panel(update, context)
        return

    welcome = db_get_setting("welcome_text").format(username=user.first_name or user.username or "کاربر")
    keyboard = [[InlineKeyboardButton("ثبت سفارش", callback_data="start_order")]]
    await update.effective_message.reply_text(welcome, reply_markup=InlineKeyboardMarkup(keyboard))


async def cb_start_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("لطفاً نام و نام خانوادگی خودتون رو وارد کنید: (لطفاً با دقت وارد کنید!)")
    return NAME

async def order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text("لطفاً نام و نام خانوادگی خودتون رو وارد کنید: (لطفاً با دقت وارد کنید!)")
    return NAME

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name"] = update.effective_message.text.strip()
    await update.effective_message.reply_text("لطفاً آدرس منزل خودتون رو وارد کنید: (لطفاً با دقت وارد کنید!)")
    return ADDRESS

async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["address"] = update.effective_message.text.strip()
    skip_kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("رد شدن از کد پستی", callback_data="skip_postal")]]
    )
    await update.effective_message.reply_text(
        "لطفاً کد پستی ۱۰ رقمی رو وارد کنید: (لطفاً با دقت وارد کنید!)",
        reply_markup=skip_kb
    )
    return POSTAL_CODE

async def skip_postal_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data["postal_code"] = ""
    await query.message.reply_text("کد پستی رد شد. لطفاً شماره موبایل خودتون رو وارد کنید (مثال: 09123456789): (لطفاً با دقت وارد کنید!)")
    return PHONE

async def get_postal_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    postal_code = update.effective_message.text.strip()
    if not re.fullmatch(r"\d{10}", postal_code):
        await update.effective_message.reply_text("کد پستی باید ۱۰ رقم باشه. لطفاً دوباره وارد کنید:")
        return POSTAL_CODE
    context.user_data["postal_code"] = postal_code
    await update.effective_message.reply_text("لطفاً شماره موبایل خودتون رو وارد کنید (مثال: 09123456789): (لطفاً با دقت وارد کنید!)")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    phone = update.effective_message.text.strip()
    if not re.fullmatch(r"09\d{9}", phone):
        await update.effective_message.reply_text("شماره موبایل باید ۱۱ رقم و با 09 شروع بشه. دوباره وارد کنید:")
        return PHONE
    context.user_data["phone"] = phone
    await update.effective_message.reply_text(
        "لطفاً عکس محصول مورد نظرتون از پیج بوتیک‌ما اسکرین‌شات بگیرید و ارسال کنید:")
    return PRODUCT_PHOTO

async def get_product_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.effective_message
    if not msg.photo:
        await msg.reply_text("لطفاً فقط عکس بفرستید.")
        return PRODUCT_PHOTO
    file_id = msg.photo[-1].file_id
    context.user_data["product_photo_id"] = file_id
    db_store_photo(update.effective_user.id, file_id)
    keyboard = [
        [InlineKeyboardButton("از قیمت اطلاع دارم!", callback_data="price_known")],
        [InlineKeyboardButton("از قیمت اطلاع ندارم!", callback_data="price_unknown")],
    ]
    await msg.reply_text("آیا از قیمت این محصول اطلاع دارید؟", reply_markup=InlineKeyboardMarkup(keyboard))
    return PRICE_AWARE

async def price_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    choice = query.data
    support = db_get_setting("support_id")
    if choice == "price_unknown":
        await query.message.reply_text(
            "اگه نیاز به پشتیبانی داری و از قیمت محصول اطمینان نداری به آیدی پشیبانی پیام بده برای راهنمایی در فرایند ثبت سفارش🥰👇🏻\n"
            f"🆔 {support}"
        )
    else:
        await query.message.reply_text("ممنونم، میریم برای ادامه فرایند ثبت سفارش ✨")

    # Size selection
    keyboard = [
        [InlineKeyboardButton("S", callback_data="S"), InlineKeyboardButton("M", callback_data="M"), InlineKeyboardButton("L", callback_data="L")],
        [InlineKeyboardButton("XL", callback_data="XL"), InlineKeyboardButton("XXL", callback_data="XXL")],
        [InlineKeyboardButton("XXXL", callback_data="XXXL"), InlineKeyboardButton("XXXXL", callback_data="XXXXL")],
        [InlineKeyboardButton("تخمین سایز از قد و وزن", callback_data="estimate_size")],
    ]
    await query.message.reply_text("لطفاً سایز مورد نظرتون رو انتخاب کنید یا برای تخمین سایز، گزینه آخر رو بزنید:",
                                   reply_markup=InlineKeyboardMarkup(keyboard))
    return SIZE

async def get_size(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    size = query.data
    if size == "estimate_size":
        await query.message.reply_text(
            "لطفاً قد (به سانتی‌متر) و وزن (به کیلوگرم) خودتون رو با فرمت زیر وارد کنید:\nقد: 170 وزن: 70")
        return SIZE
    context.user_data["size"] = size
    return await review_and_prepay(query.message, context)

async def process_size_estimation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.effective_message.text
    try:
        h_match = re.search(r"قد:\s*(\d+)", text)
        w_match = re.search(r"وزن:\s*(\d+)", text)
        if not (h_match and w_match):
            raise ValueError
        height = int(h_match.group(1))
        weight = int(w_match.group(1))
        size = estimate_size(height, weight)
        context.user_data["size"] = size
        return await review_and_prepay(update.effective_message, context)
    except Exception:
        await update.effective_message.reply_text("فرمت اشتباهه! لطفاً مثل این وارد کنید:\nقد: 170 وزن: 70")
        return SIZE

async def review_and_prepay(msg_source, context: ContextTypes.DEFAULT_TYPE) -> int:
    ud = context.user_data
    summary = (
        f"سفارش شما:\n"
        f"نام: {ud.get('name','')}\n"
        f"آدرس: {ud.get('address','')}\n"
        f"کد پستی: {ud.get('postal_code','')}\n"
        f"شماره موبایل: {ud.get('phone','')}\n"
        f"سایز: {ud.get('size','')}\n\n"
    )
    keyboard = [
        [InlineKeyboardButton("ویرایش نام", callback_data="edit_name"), InlineKeyboardButton("ویرایش آدرس", callback_data="edit_address")],
        [InlineKeyboardButton("ویرایش کدپستی", callback_data="edit_postal"), InlineKeyboardButton("ویرایش موبایل", callback_data="edit_phone")],
        [InlineKeyboardButton("ادامه", callback_data="go_prepay")],
    ]
    await msg_source.reply_text(summary + "(لطفاً در صورت نیاز ویرایش کنید)", reply_markup=InlineKeyboardMarkup(keyboard))
    return SIZE

async def edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    key = query.data
    prompts = {
        "edit_name": "نام جدید را وارد کنید:",
        "edit_address": "آدرس جدید را وارد کنید:",
        "edit_postal": "کد پستی جدید (۱۰ رقم) را وارد کنید:",
        "edit_phone": "شماره موبایل جدید را وارد کنید:",
    }
    context.user_data["_edit_key"] = key
    await query.message.reply_text(prompts[key])
    return SIZE

async def handle_edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    key = context.user_data.get("_edit_key")
    if not key:
        # treat as size estimation attempt
        return await process_size_estimation(update, context)

    text = update.effective_message.text.strip()
    if key == "edit_name":
        context.user_data["name"] = text
    elif key == "edit_address":
        context.user_data["address"] = text
    elif key == "edit_postal":
        if not re.fullmatch(r"\d{10}", text):
            await update.effective_message.reply_text("کد پستی باید ۱۰ رقم باشه. دوباره وارد کنید:")
            return SIZE
        context.user_data["postal_code"] = text
    elif key == "edit_phone":
        if not re.fullmatch(r"09\d{9}", text):
            await update.effective_message.reply_text("شماره موبایل باید ۱۱ رقم و با 09 شروع بشه. دوباره وارد کنید:")
            return SIZE
        context.user_data["phone"] = text

    context.user_data.pop("_edit_key", None)
    await update.effective_message.reply_text("به‌روزرسانی شد ✅")
    return await review_and_prepay(update.effective_message, context)

async def go_prepay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    prepay = db_get_setting("prepay_text")
    await query.message.reply_text(prepay)

    card_msg = db_get_setting("card_text").format(
        card_number=card_info["current_card"],
        owner_name=db_get_setting("card_owner") or "صحرا",
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("کپی شماره کارت", callback_data="copy_card")]])
    sent_card = await query.message.reply_text(card_msg, reply_markup=kb)
    db_store_card_message(
        sent_card.chat_id,
        sent_card.message_id,
        getattr(sent_card, "business_connection_id", None),
    )
    await query.message.reply_text("سپس اسکرین‌شات واریزی رو بفرستید.")
    return CONFIRM_PAYMENT

async def copy_card_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    # Sending number in monospace makes it easy to long-press/copy on mobile
    await query.message.reply_text(f"شماره کارت:\n`{card_info['current_card']}`", parse_mode="Markdown")

async def confirm_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.effective_message
    # accept as photo OR image/* document
    file_id = None
    if msg.photo:
        file_id = msg.photo[-1].file_id
    elif msg.document and msg.document.mime_type and msg.document.mime_type.startswith("image/"):
        file_id = msg.document.file_id

    if file_id:
        context.user_data["payment_screenshot"] = True
        context.user_data["payment_file_id"] = file_id

        # Send every received payment receipt to all configured admins immediately.
        customer = update.effective_user
        customer_name = customer.full_name if customer else "نامشخص"
        receipt_caption = (
            f"🧾 رسید جدید مشتری\n"
            f"نام تلگرام: {customer_name}\n"
            f"آیدی عددی: {customer.id if customer else 'نامشخص'}"
        )
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_photo(chat_id=admin_id, photo=file_id, caption=receipt_caption)
            except Exception:
                logger.exception("Could not send receipt to admin %s", admin_id)

        keyboard = [
            [InlineKeyboardButton("بله، واریز کردم", callback_data="payment_confirmed")],
            [InlineKeyboardButton("خیر، هنوز واریز نکردم", callback_data="payment_not_confirmed")],
        ]
        await msg.reply_text("واریز انجام شد؟", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await msg.reply_text("لطفاً اسکرین‌شات واریزی رو بفرستید (به صورت عکس).")
    return CONFIRM_PAYMENT

async def payment_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "payment_confirmed":
        order_data = dict(context.user_data)
        order_data.setdefault("status", "active")
        orders[user_id] = order_data
        save_data()
        await query.message.reply_text(db_get_setting("success_text"))
        return ConversationHandler.END

    # Not confirmed — nudge
    keyboard = [
        [InlineKeyboardButton("بله، واریز کردم", callback_data="payment_confirmed")],
        [InlineKeyboardButton("خیر، هنوز واریز نکردم", callback_data="payment_not_confirmed")],
    ]
    await query.message.reply_text("واریز کردید یا خیر؟ محصول داره تموم میشه!", reply_markup=InlineKeyboardMarkup(keyboard))
    return CONFIRM_PAYMENT


# ----- Admin panel & commands -----
async def send_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not is_admin(user.id):
        return
    panel_text = "پنل ادمین — یکی از گزینه‌ها را انتخاب کنید:"
    kb = [
        [InlineKeyboardButton("سفارش‌ها", callback_data="admin_orders"),
         InlineKeyboardButton("سفارش‌های تکمیل‌شده", callback_data="admin_fulfilled")],
        [InlineKeyboardButton("ویرایش پیام‌ها", callback_data="admin_edit_texts"),
         InlineKeyboardButton("پشتیبان", callback_data="admin_support")],
        [InlineKeyboardButton("تغییر متن کارت/پرداخت", callback_data="admin_pick_text:card_text")],
        [InlineKeyboardButton("🗑 پاک کردن شماره کارت از چت مشتری‌ها", callback_data="admin_delete_card_messages")],
        [InlineKeyboardButton("شروع ثبت سفارش (نمای مشتری)", callback_data="start_order")],
        [InlineKeyboardButton("❗️ حذف همه داده‌ها", callback_data="admin_wipe_all")],
    ]
    await update.effective_message.reply_text(panel_text, reply_markup=InlineKeyboardMarkup(kb))

async def admin_panel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("⛔️ این بخش مخصوص ادمین‌هاست.")
        return
    await send_admin_panel(update, context)

async def admin_help_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.message.reply_text("⛔️ این بخش مخصوص ادمین‌هاست.")
        return
    await query.message.reply_text(
        "دستورات ادمین:\n"
        "/change_card <card> — تغییر شماره کارت\n"
        "/orders — مشاهده خلاصه سفارش‌ها (۱۰ مورد آخر)\n"
        "/set_text <key> <value> — تنظیم متن‌ها (welcome_text|prepay_text|success_text|support_id|card_text|card_owner)\n"
        "/get_texts — مشاهده متن‌های فعلی\n"
        "/support — نمایش آیدی پشتیبان\n"
        "/panel — نمایش پنل ادمین"
    )

async def send_order_card(query, uid: int, o: Dict[str, Any], fulfilled: bool) -> None:
    product_file_id = get_last_product_photo(uid)
    payment_file_id = o.get("payment_file_id")
    caption = (
        f"سفارش کاربر {uid}:\n"
        f"نام: {o.get('name','?')}\n"
        f"آدرس: {o.get('address','?')}\n"
        f"کدپستی: {o.get('postal_code','?')}\n"
        f"موبایل: {o.get('phone','?')}\n"
        f"سایز: {o.get('size','?')}\n"
        f"وضعیت: {o.get('status','active')}"
    )
    if fulfilled:
        buttons = [[InlineKeyboardButton("حذف", callback_data=f"admin_delete:{uid}")]]
    else:
        buttons = [[
            InlineKeyboardButton("حذف", callback_data=f"admin_delete:{uid}"),
            InlineKeyboardButton("تکمیل شد", callback_data=f"admin_done:{uid}")
        ]]
    markup = InlineKeyboardMarkup(buttons)

    if product_file_id:
        await query.message.reply_photo(photo=product_file_id, caption=caption, reply_markup=markup)
    else:
        await query.message.reply_text(caption, reply_markup=markup)

    if payment_file_id:
        await query.message.reply_photo(photo=payment_file_id, caption="رسید پرداخت")

async def admin_orders_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.message.reply_text("⛔️ این بخش مخصوص ادمین‌هاست.")
        return
    any_sent = False
    for uid, o in list(orders.items()):
        if o.get("status", "active") == "fulfilled":
            continue
        await send_order_card(query, uid, o, fulfilled=False)
        any_sent = True
    if not any_sent:
        await query.message.reply_text("هیچ سفارش فعالی وجود ندارد.")

async def admin_fulfilled_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.message.reply_text("⛔️ این بخش مخصوص ادمین‌هاست.")
        return
    any_sent = False
    for uid, o in list(orders.items()):
        if o.get("status") == "fulfilled":
            await send_order_card(query, uid, o, fulfilled=True)
            any_sent = True
    if not any_sent:
        await query.message.reply_text("سفارش تکمیل‌شده‌ای وجود ندارد.")

async def admin_order_delete_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.message.reply_text("⛔️ این بخش مخصوص ادمین‌هاست.")
        return
    uid = int(query.data.split(":", 1)[1])
    if uid in orders:
        del orders[uid]
        save_data()
        await query.message.reply_text("سفارش حذف شد ✅")
    else:
        await query.message.reply_text("سفارش پیدا نشد.")

async def admin_order_done_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.message.reply_text("⛔️ این بخش مخصوص ادمین‌هاست.")
        return
    uid = int(query.data.split(":", 1)[1])
    if uid in orders:
        orders[uid]["status"] = "fulfilled"
        save_data()
        await query.message.reply_text("سفارش به عنوان تکمیل‌شده علامت خورد ✅")
    else:
        await query.message.reply_text("سفارش پیدا نشد.")

async def admin_support_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.message.reply_text("⛔️ این بخش مخصوص ادمین‌هاست.")
        return
    await query.message.reply_text(f"لطفاً به این آیدی پیام بدید: {db_get_setting('support_id')}")

async def admin_edit_texts_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.message.reply_text("⛔️ این بخش مخصوص ادمین‌هاست.")
        return
    keys = [
        ("welcome_text", "پیام خوش‌آمد"),
        ("prepay_text", "نکات قبل از پرداخت"),
        ("success_text", "پیام موفقیت پرداخت"),
        ("support_id", "آیدی پشتیبان"),
        ("card_text", "متن کارت/پرداخت"),
        ("card_owner", "نام صاحب کارت"),
    ]
    rows = [[InlineKeyboardButton(label, callback_data=f"admin_pick_text:{key}")] for key, label in keys]
    await query.message.reply_text("کدام متن را می‌خواهید تغییر دهید؟", reply_markup=InlineKeyboardMarkup(rows))

async def admin_pick_text_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.message.reply_text("⛔️ این بخش مخصوص ادمین‌هاست.")
        return
    key = query.data.split(":", 1)[1]
    current = db_get_setting(key)
    context.user_data["edit_key"] = key
    context.user_data.pop("edit_value", None)
    await query.message.reply_text(f"متن فعلی:\n\n{current}\n\nاین متن فعلی است. لطفاً متن جدید را ارسال کنید.")

async def admin_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not (update.effective_user and is_admin(update.effective_user.id)):
        return
    key = context.user_data.get("edit_key")
    if not key:
        return
    context.user_data["edit_value"] = update.effective_message.text
    kb = [[InlineKeyboardButton("تأیید", callback_data="admin_text_confirm:yes"),
           InlineKeyboardButton("انصراف", callback_data="admin_text_confirm:no")]]
    await update.effective_message.reply_text(
        "آیا می‌خواهید متن انتخاب‌شده با این متن جدید جایگزین شود؟", reply_markup=InlineKeyboardMarkup(kb)
    )

async def admin_text_confirm_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.message.reply_text("⛔️ این بخش مخصوص ادمین‌هاست.")
        return
    decision = query.data.split(":", 1)[1]
    key = context.user_data.get("edit_key")
    val = context.user_data.get("edit_value")
    if decision == "yes" and key and val is not None:
        db_set_setting(key, val)
        context.user_data.pop("edit_key", None)
        context.user_data.pop("edit_value", None)
        await query.message.reply_text("متن با موفقیت به‌روزرسانی شد ✅")
    else:
        context.user_data.pop("edit_key", None)
        context.user_data.pop("edit_value", None)
        await query.message.reply_text("عملیات لغو شد.")

async def admin_delete_card_messages_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.message.reply_text("⛔️ این بخش مخصوص ادمین‌هاست.")
        return

    rows = db_get_card_messages()
    if not rows:
        await query.message.reply_text("هیچ پیام شماره کارتی برای پاک کردن ثبت نشده.")
        return

    deleted = 0
    failed = 0
    for row_id, chat_id, message_id, business_connection_id in rows:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
            db_delete_card_message_record(row_id)
            deleted += 1
        except Exception:
            # Keep failed records so the admin can retry later.
            failed += 1
            logger.exception("Could not delete card message chat=%s message=%s", chat_id, message_id)

    await query.message.reply_text(
        f"✅ {deleted} پیام شماره کارت از چت مشتری‌ها پاک شد."
        + (f"\n⚠️ {failed} پیام پاک نشد؛ احتمالاً دسترسی حذف پیام یا محدودیت زمانی تلگرام اجازه نداده." if failed else "")
    )

async def admin_wipe_all_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.message.reply_text("⛔️ این بخش مخصوص ادمین‌هاست.")
        return
    text = (
        "⚠️ آیا از حذف *همه‌ی داده‌های سفارش* مطمئن هستید؟\n"
        "این کار *غیرقابل بازگشت* است و شامل:\n"
        "• تمام سفارش‌ها (فعال و تکمیل‌شده)\n"
        "• تمام تصاویر محصولات\n"
        "می‌شود."
    )
    kb = [[
        InlineKeyboardButton("بله، حذف کن ✅", callback_data="admin_wipe_all_confirm:yes"),
        InlineKeyboardButton("نه، منصرف شدم ❌", callback_data="admin_wipe_all_confirm:no"),
    ]]
    await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def admin_wipe_all_confirm_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not is_admin(query.from_user.id):
        await query.message.reply_text("⛔️ این بخش مخصوص ادمین‌هاست.")
        return
    decision = query.data.split(":", 1)[1]
    if decision == "yes":
        orders.clear()
        save_data()
        db_delete_all_images()
        await query.message.reply_text("✅ همه‌ی سفارش‌ها و تصاویر با موفقیت حذف شدند.")
    else:
        await query.message.reply_text("عملیات لغو شد.")


# ----- Admin classic commands -----
async def change_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("⛔️ فقط ادمین‌ها می‌تونن شماره کارت رو تغییر بدن.")
        return
    if not context.args:
        await update.effective_message.reply_text("لطفاً شماره کارت جدید رو وارد کنید (مثال: /change_card 1234-5678-9012-3456):")
        return
    new_card = context.args[0]
    if not re.fullmatch(r"\d{4}-\d{4}-\d{4}-\d{4}", new_card):
        await update.effective_message.reply_text("شماره کارت باید به فرمت 1234-5678-9012-3456 باشه. دوباره امتحان کنید:")
        return
    card_info["current_card"] = new_card
    save_data()
    await update.effective_message.reply_text(f"شماره کارت جدید ({new_card}) با موفقیت ثبت شد!")

async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("⛔️ این بخش مخصوص ادمین‌هاست.")
        return
    msg = (
        "دستورات ادمین:\n"
        "/change_card <card> — تغییر شماره کارت\n"
        "/orders — مشاهده خلاصه سفارش‌ها (۱۰ مورد آخر)\n"
        "/set_text <key> <value> — تنظیم متن‌ها (welcome_text|prepay_text|success_text|support_id|card_text|card_owner)\n"
        "/get_texts — مشاهده متن‌های فعلی\n"
        "/support — نمایش آیدی پشتیبان\n"
        "/panel — نمایش پنل ادمین"
    )
    await update.effective_message.reply_text(msg)

async def list_orders(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("⛔️ این بخش مخصوص ادمین‌هاست.")
        return
    if not orders:
        await update.effective_message.reply_text("هنوز سفارشی ثبت نشده.")
        return
    items = list(orders.items())[-10:]
    lines = []
    for uid, o in items:
        lines.append(f"• {o.get('name','?')} — سایز {o.get('size','?')}\n  تلفن: {o.get('phone','?')} | کدپستی: {o.get('postal_code','?')}")
    await update.effective_message.reply_text("آخرین سفارش‌ها (تا ۱۰ مورد):\n\n" + "\n".join(lines) + f"\n\nتعداد کل سفارش‌ها: {len(orders)}")

async def set_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("⛔️ این بخش مخصوص ادمین‌هاست.")
        return
    if len(context.args) < 2:
        await update.effective_message.reply_text("استفاده: /set_text <welcome_text|prepay_text|success_text|support_id|card_text|card_owner> <value>")
        return
    key = context.args[0]
    value = " ".join(context.args[1:])
    if key not in {"welcome_text", "prepay_text", "success_text", "support_id", "card_text", "card_owner"}:
        await update.effective_message.reply_text("کلید نامعتبر.")
        return
    db_set_setting(key, value)
    await update.effective_message.reply_text("ثبت شد ✅")

async def get_texts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("⛔️ این بخش مخصوص ادمین‌هاست.")
        return
    keys = ["welcome_text", "prepay_text", "success_text", "support_id", "card_text", "card_owner"]
    parts = [f"{k}:\n{db_get_setting(k)}" for k in keys]
    await update.effective_message.reply_text("\n\n".join(parts))

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_admin(update.effective_user.id):
        await update.effective_message.reply_text("⛔️ این بخش مخصوص ادمین‌هاست.")
        return
    await update.effective_message.reply_text(f"لطفاً به این آیدی پیام بدید: {db_get_setting('support_id')}")

async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(f"Your Telegram user_id: {update.effective_user.id}")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.effective_message.reply_text("سفارش لغو شد. برای شروع دوباره، دکمه 'ثبت سفارش' را بزنید.")
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Update %s caused error: %s", update, context.error)
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text("یه مشکلی پیش اومد! لطفاً دوباره امتحان کنید.")
    except Exception:
        pass


def main() -> None:
    load_data()
    db_init()

    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN is not set. Add it as an environment variable before running the bot.")

    # Telegram Business update/filter support requires python-telegram-bot 21.1+.
    application = Application.builder().token(token).build()

    conv_handler = ConversationHandler(
        entry_points=[
            # Telegram Business: the customer's first incoming message starts the flow.
            MessageHandler(
                filters.UpdateType.BUSINESS_MESSAGE,
                business_first_message,
            ),
            CommandHandler("order", order),
            CallbackQueryHandler(cb_start_order, pattern=r"^start_order$")
        ],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            POSTAL_CODE: [
                CallbackQueryHandler(skip_postal_cb, pattern=r"^skip_postal$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_postal_code),
            ],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            PRODUCT_PHOTO: [MessageHandler(filters.PHOTO, get_product_photo)],
            PRICE_AWARE: [CallbackQueryHandler(price_choice, pattern=r"^(price_known|price_unknown)$")],
            SIZE: [
                CallbackQueryHandler(get_size, pattern=r"^(S|M|L|XL|XXL|XXXL|XXXXL|estimate_size)$"),
                CallbackQueryHandler(edit_field, pattern=r"^(edit_name|edit_address|edit_postal|edit_phone)$"),
                CallbackQueryHandler(go_prepay, pattern=r"^go_prepay$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_edit_input),
            ],
            CONFIRM_PAYMENT: [
                MessageHandler(filters.PHOTO | filters.Document.ALL, confirm_payment),
                CallbackQueryHandler(payment_confirmation, pattern=r"^(payment_confirmed|payment_not_confirmed)$"),
                CallbackQueryHandler(copy_card_cb, pattern=r"^copy_card$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    # Public / Admin commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("panel", admin_panel_cmd))
    application.add_handler(CommandHandler("change_card", change_card))
    application.add_handler(CommandHandler("admin_help", admin_help))
    application.add_handler(CommandHandler("whoami", whoami))
    application.add_handler(CommandHandler("orders", list_orders))
    application.add_handler(CommandHandler("set_text", set_text))
    application.add_handler(CommandHandler("get_texts", get_texts))
    application.add_handler(CommandHandler("support", support))

    # Conversation + Admin panel callbacks
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(admin_help_cb, pattern=r"^admin_help$"))
    application.add_handler(CallbackQueryHandler(admin_orders_cb, pattern=r"^admin_orders$"))
    application.add_handler(CallbackQueryHandler(admin_fulfilled_cb, pattern=r"^admin_fulfilled$"))
    application.add_handler(CallbackQueryHandler(admin_support_cb, pattern=r"^admin_support$"))
    application.add_handler(CallbackQueryHandler(admin_edit_texts_cb, pattern=r"^admin_edit_texts$"))
    application.add_handler(CallbackQueryHandler(admin_pick_text_cb, pattern=r"^admin_pick_text:.+"))
    application.add_handler(CallbackQueryHandler(admin_text_confirm_cb, pattern=r"^admin_text_confirm:(yes|no)$"))
    application.add_handler(CallbackQueryHandler(admin_order_delete_cb, pattern=r"^admin_delete:\d+$"))
    application.add_handler(CallbackQueryHandler(admin_order_done_cb, pattern=r"^admin_done:\d+$"))
    application.add_handler(CallbackQueryHandler(admin_delete_card_messages_cb, pattern=r"^admin_delete_card_messages$"))
    application.add_handler(CallbackQueryHandler(admin_wipe_all_cb, pattern=r"^admin_wipe_all$"))
    application.add_handler(CallbackQueryHandler(admin_wipe_all_confirm_cb, pattern=r"^admin_wipe_all_confirm:(yes|no)$"))

    # Admin text input listener (non-command text) – keep it last so it doesn't eat earlier steps
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_input))

    application.add_error_handler(error_handler)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
