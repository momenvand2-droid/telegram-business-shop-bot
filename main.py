import os
import re
import json
import time
import random
import sqlite3
import unicodedata
from difflib import SequenceMatcher
from datetime import datetime
import requests
from response_bank_100k import RESPONSES

# ============================================================
# Telegram Business Shop Bot v9.3
# Conversational Persian sales assistant
# ============================================================

TOKEN = os.environ["BOT_TOKEN"].strip()
ADMIN_ID = int(os.environ["ADMIN_ID"]) if os.environ.get("ADMIN_ID") else 0
API = f"https://api.telegram.org/bot{TOKEN}"
DB_PATH = os.environ.get("DB_PATH", "shop.db")

PRICE_MIN = 799_000
PRICE_MAX = 2_000_000
SHIPPING_FEE = 112_000
MAX_ITEMS_PER_ORDER = 50

# ------------------------------------------------------------
# Response banks
# Responses are assembled from several independent banks.
# This creates a very large number of natural combinations
# without hard-coding 100,000 near-identical sentences.
# ------------------------------------------------------------

FRIENDLY_OPENERS = [
    "حتماً عزیز 🌹",
    "آره حتماً 👌",
    "چشم رفیق 🤝",
    "حتماً، بریم جلو 👌",
    "اوکی عزیز 🌹",
    "آره، متوجه‌ام 👌",
    "قربونت، حتماً 🌹",
    "باشه، الان میگم 👌",
    "حتماً داداش 😄",
    "روی چشم 🌹",
    "آره عزیز،",
    "چشم،",
]

SOFT_CLOSERS = [
    "هرچی دیگه خواستی بپرس 🌹",
    "اگه چیزی مبهمه بگو تا واضح‌تر بگم.",
    "من هستم، هر سوالی داری بپرس 👌",
    "اگر خواستی بیشتر راهنماییت می‌کنم.",
    "هرجا گیر کردی بگو باهم جلو می‌ریم.",
    "نگران نباش، مرحله‌به‌مرحله باهم می‌ریم جلو 🌹",
    "",
]

GREETINGS = [
    "سلام عزیز 👋 خوش اومدی 🌹 اسم یا عکس محصولی که مدنظرت هست رو بفرست.",
    "سلام رفیق 👋 خوش اومدی. قیمت، سایز، ارسال یا ثبت سفارش؛ هرچی خواستی بپرس.",
    "سلام 🌹 در خدمتم. محصول رو بفرست تا راهنماییت کنم.",
    "سلام داداش 👋 خوش اومدی. بگو دنبال چی هستی تا سریع راهنماییت کنم.",
    "سلام عزیزم 🌹 عکس یا اسم کار رو بفرست، بریم ببینیم چی به دردت می‌خوره.",
]

UNKNOWN_REPLIES = [
    "منظورت رو کامل نگرفتم 😅 یه مدل دیگه بگو تا دقیق جواب بدم.",
    "یکم واضح‌تر می‌گی عزیز؟ می‌خوام درست متوجه منظورت بشم 🌹",
    "این یکی رو دقیق نگرفتم؛ کوتاه‌تر یا با یه عبارت دیگه بگو 👌",
    "فکر کنم منظورت رو اشتباه گرفتم 😄 دوباره یه جور دیگه بگو.",
    "یه بار دیگه با کلمات ساده‌تر بگو رفیق، دقیق جواب می‌دم.",
    "این جمله برام دوپهلو بود؛ منظورت رو یه کم بازتر بگو 🌹",
    "متوجه نشدم دقیقاً کدوم بخش رو می‌پرسی. یه جور دیگه بگو 👌",
    "پیامت رو گرفتم ولی منظورت رو نه 😅 یه بار دیگه بگو.",
]

WAIT_REPLIES = [
    "باشه عزیز، عجله‌ای نیست 😄 هر وقت آماده بودی ادامه می‌دیم.",
    "چشم، منتظرم 👌 هر وقت آماده شدی پیام بده.",
    "باشه رفیق 🌹 من هستم، با خیال راحت.",
    "اوکی، عجله نکن. هر وقت آماده بودی از همین‌جا ادامه می‌دیم.",
]

DONT_KNOW_GENERIC = [
    "اشکالی نداره 😄 بگو دقیقاً کدوم قسمتش رو نمی‌دونی تا همون رو برات ساده کنم.",
    "اوکی، من راهنماییت می‌کنم 👌 فقط بگو کجاش برات نامشخصه.",
    "نگران نباش؛ لازم نیست همه‌چی رو بدونی. ازت یکی‌یکی می‌پرسم 🌹",
]

PRICE_DIFF_REPLIES = [
    "قیمتا آپدیت شدن 🌹",
    "قیمتا آپدیت شدن عزیز 👌",
    "قیمت‌های جدید آپدیت شدن 🌹",
]

SHIPPING_METHOD_REPLIES = [
    "ارسال ما فقط با پست پیشتاز انجام می‌شه 📦 تیپاکس، باربری، اتوبوس و روش‌های دیگه نداریم.",
    "برای همه سفارش‌ها فقط پست پیشتاز داریم عزیز 🌹 امکان ارسال با تیپاکس یا باربری نداریم.",
    "روش ارسال فروشگاه فقط پست پیشتازه 📮 برای نظم سفارش‌ها از روش دیگه‌ای ارسال نمی‌کنیم.",
    "فقط پست پیشتاز داریم رفیق 👌 ارسال با اتوبوس، باربری، تیپاکس یا پیک انجام نمی‌شه.",
]

SHIPPING_COST_REPLIES = [
    "هزینه ارسال کل سفارش فقط ۱۱۲٬۰۰۰ تومنه؛ از ۱ تا ۵۰ محصول همین یک هزینه حساب می‌شه 📦",
    "پست کل سفارش ۱۱۲ هزار تومنه ✅ تعداد محصول تا سقف ۵۰ تا روی هزینه ارسال تغییری نمی‌ده.",
    "هزینه پست ثابته: ۱۱۲٬۰۰۰ تومان برای کل سبد، نه برای هر محصول 🌹",
    "چه یک محصول بگیری چه چندتا تا سقف ۵۰ عدد، هزینه ارسال کل سفارش ۱۱۲ هزار تومنه.",
]

SHIPPING_CHEAP_REPLIES = [
    "به خاطر قرارداد روزانه با اداره پست و ارسال تعداد بالا، هزینه ارسال برامون مناسب‌تر درمیاد 📦",
    "چون ارسال روزانه‌مون بالاست و با اداره پست قرارداد داریم، هزینه پست برای مشتری ثابت و کمتر حساب می‌شه 🌹",
    "به خاطر تعداد بالای ارسال و قرارداد روزانه با اداره پست، هزینه کل ارسال رو ۱۱۲ هزار تومان نگه داشتیم 👌",
]

SHIPPING_TIME_REPLIES = [
    "آماده‌سازی و تحویل سفارش به پست معمولاً ۳ تا ۵ روز کاری زمان می‌بره و رسیدن مرسوله معمولاً حدود ۸ تا ۱۲ روزه 📦",
    "معمولاً ۳ تا ۵ روز کاری برای آماده‌سازی و ارسال در نظر بگیر؛ رسیدن بسته هم معمولاً حدود ۸ تا ۱۲ روز زمان می‌بره.",
    "سفارش طی حدود ۳ تا ۵ روز کاری وارد فرایند ارسال می‌شه و مرسوله معمولاً حدود ۸ تا ۱۲ روزه به دستت می‌رسه 🌹",
]

SHIPPING_DAYS_REPLIES = [
    "ارسال‌ها شنبه تا پنجشنبه انجام می‌شن؛ جمعه ارسال نداریم 📦",
    "روزهای ارسال فروشگاه از شنبه تا پنجشنبه‌ست و جمعه مرسوله تحویل پست نمی‌شه.",
    "مرسوله‌ها شنبه تا پنجشنبه ارسال می‌شن عزیز 🌹 جمعه ارسال نداریم.",
]

LATE_DELIVERY_REPLIES = [
    "صبور باشین لطفاً 🌹 سفارش وارد فرایند ارسال شده؛ به خاطر تعداد بالای مرسوله‌ها ثبت یا نمایش کد رهگیری بعضی وقت‌ها با تأخیر انجام می‌شه.",
    "نگران نباشین 📦 بعضی وقت‌ها به دلیل حجم بالای ارسال‌ها، ثبت کد رهگیری کمی دیرتر انجام می‌شه.",
    "مرسوله در فرایند ارساله 🌹 به خاطر تعداد زیاد ارسال‌ها ممکنه ثبت کد ارسالی با کمی تأخیر انجام بشه.",
]

LOW_PRICE_REPLIES = [
    "سعی می‌کنیم قیمت‌گذاری رو با حاشیه سود پایین‌تر و متناسب با موجودی انجام بدیم، برای همین بعضی مدل‌ها اقتصادی‌تر درمیاد 🌹",
    "قیمت بعضی کارها به خاطر شرایط تأمین و حجم فروش پایین‌تر از معمول درمیاد. مشخصات هر محصول رو هم قبل از خرید می‌تونی جدا بپرسی 👌",
    "قیمت‌ها بسته به موجودی و شرایط تأمین فرق می‌کنن و تا جای ممکن اقتصادی حساب می‌کنیم.",
    "روی بعضی مدل‌ها سود رو کمتر می‌گیریم تا قیمت نهایی مناسب‌تر باشه 🌹",
]

PRODUCT_QUALITY_REPLIES = [
    "برای کیفیت یا جنس یک کار خاص، اسم یا عکس همون محصول رو بفرست تا درباره همون مدل راهنماییت کنم.",
    "جنس هر مدل ممکنه فرق کنه؛ عکس یا اسم محصول رو بفرست تا دقیق‌تر بگم 👌",
    "اگه منظورت کیفیت یه محصول خاصه، همون کار رو بفرست تا اشتباهی درباره مدل دیگه جواب ندم 🌹",
]

RETURN_REPLIES = [
    "شرایط تعویض یا مرجوعی باید بر اساس قوانین خود فروشگاه تأیید بشه. اگر محصول خاصی مدنظرته بگو تا موضوع رو برای سفارش همون مورد ثبت کنیم.",
    "برای تعویض و مرجوعی بهتره شرایط سفارش مشخص باشه؛ شماره سفارش یا محصول رو بفرست تا دقیق‌تر راهنماییت کنم.",
]

STOCK_REPLIES = [
    "بله موجوده ✅ سایزهای S تا 4XL هم موجودن 🌹",
    "آره عزیز، موجوده ✅ S / M / L / XL / 2XL / 3XL / 4XL هم داریم 👌",
    "بله این کار موجوده ✅ سایزبندی کامل S تا 4XL موجوده.",
]

COLOR_REPLIES = [
    "اسم یا عکس محصول رو بفرست و بگو چه رنگی مدنظرته تا دقیق‌تر راهنماییت کنم 🌹",
    "رنگ‌بندی برای هر مدل فرق می‌کنه؛ محصول رو بفرست تا درباره همون کار صحبت کنیم 👌",
]

SIZE_ASK_REPLIES = [
    "قد و وزنت رو بفرست؛ مثلاً «قد ۱۸۰ وزن ۸۰». اگه فیت آزاد یا جذب دوست داری اونم بگو 👌",
    "برای پیشنهاد سایز، قد + وزن رو بگو و بگو لباس رو معمولی می‌پوشی یا آزاد 🌹",
    "قد و وزن رو بده رفیق؛ یه سایز تقریبی بهت پیشنهاد می‌دم. اگه دور سینه هم داشته باشی دقیق‌تر می‌شه.",
]

# ------------------------------------------------------------
# Text normalization and fuzzy understanding
# ------------------------------------------------------------

PERSIAN_DIGITS = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
    "01234567890123456789"
)

# Common Persian chat typos/slang. It is deliberately compact:
# fuzzy matching below also covers unseen misspellings.
TOKEN_CANON = {
    "میخوام": "میخوام",
    "میخام": "میخوام",
    "میخاهم": "میخوام",
    "میخوامش": "میخوام",
    "میخای": "میخوای",
    "میخاهی": "میخوای",
    "میخامش": "میخوام",
    "چندع": "چنده",
    "چندست": "چنده",
    "چقد": "چقدر",
    "چقذر": "چقدر",
    "قیمتش": "قیمت",
    "قیمط": "قیمت",
    "گیمت": "قیمت",
    "قیمتو": "قیمت",
    "ارسالوت": "ارسال",
    "ارسالش": "ارسال",
    "ارسال": "ارسال",
    "پوصت": "پست",
    "پصت": "پست",
    "پستش": "پست",
    "تیباکس": "تیپاکس",
    "تیپاکث": "تیپاکس",
    "سایض": "سایز",
    "سایس": "سایز",
    "سایزش": "سایز",
    "وزنم": "وزن",
    "قدم": "قد",
    "نمدونم": "نمیدونم",
    "نمیدونم": "نمیدونم",
    "نمیدنم": "نمیدونم",
    "نمیدانم": "نمیدونم",
    "نمیفهمم": "نمیفهمم",
    "چیمیگی": "چی میگی",
    "چیمگی": "چی میگی",
    "چیگفتی": "چی گفتی",
    "وایسا": "وایسا",
    "وایستا": "وایسا",
    "صبرکن": "صبر کن",
    "شماره": "شماره",
    "شمارع": "شماره",
    "موبایل": "موبایل",
    "موبایل": "موبایل",
    "ادرس": "آدرس",
    "آدرص": "آدرس",
    "فامیلی": "فامیلی",
    "فامیل": "فامیلی",
    "مرجوع": "مرجوعی",
    "تعویضش": "تعویض",
    "اورج": "اورجینال",
    "اورجیناله": "اورجینال",
}

def normalize_text(text):
    text = unicodedata.normalize("NFKC", text or "")
    text = text.translate(PERSIAN_DIGITS)
    text = text.replace("ي", "ی").replace("ك", "ک").replace("ۀ", "ه").replace("ة", "ه")
    text = text.replace("\u200c", " ")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s\u0600-\u06FF]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    words = []
    for token in text.split():
        words.append(TOKEN_CANON.get(token, token))
    return " ".join(words)

def similarity(a, b):
    a, b = normalize_text(a), normalize_text(b)
    if not a or not b:
        return 0.0
    if a in b or b in a:
        shorter = min(len(a), len(b))
        longer = max(len(a), len(b))
        if shorter >= 3:
            return max(0.88, shorter / max(longer, 1))
    seq = SequenceMatcher(None, a, b).ratio()
    aw, bw = set(a.split()), set(b.split())
    jac = len(aw & bw) / max(1, len(aw | bw))
    return max(seq, jac)

def fuzzy_any(text, phrases, threshold=0.70):
    n = normalize_text(text)
    if not n:
        return False
    if any(normalize_text(p) in n for p in phrases):
        return True

    words = n.split()
    # Compare phrase against local n-grams too, so typos inside long sentences
    # do not destroy intent recognition.
    for phrase in phrases:
        p = normalize_text(phrase)
        pw = p.split()
        sizes = range(max(1, len(pw)-1), min(len(words), len(pw)+2)+1)
        for size in sizes:
            for i in range(0, len(words)-size+1):
                chunk = " ".join(words[i:i+size])
                if similarity(chunk, p) >= threshold:
                    return True
    return False

INTENTS = {
    "greeting": ["سلام", "درود", "سلام خوبی", "سلام وقت بخیر", "hello", "hi"],
    "wait": ["وایسا", "صبر کن", "یه لحظه", "الان نه", "فعلا صبر کن", "باش تا بگم"],
    "confused": ["چی میگی", "چی گفتی", "منظورت چیه", "نفهمیدم", "نمیفهمم", "چی باید بفرستم"],
    "dont_know": ["نمیدونم", "نمی دونم", "اطلاع ندارم", "بلد نیستم", "نمدونم"],
    "thanks": ["مرسی", "ممنون", "دمت گرم", "تشکر", "سپاس"],
    "bye": ["خدافظ", "خداحافظ", "فعلا", "بای", "روز خوش"],
    "order": ["ثبت سفارش", "سفارش میخوام", "میخوام بخرم", "خرید کنم", "سفارش", "بخرم"],
    "price": ["قیمت چنده", "چنده", "قیمت", "چقدر قیمت", "تومن", "تومان"],
    "price_difference": ["چرا قیمت پیج فرق", "قیمت داخل پیج فرق", "پیج ارزونتر", "پیج گرونتر"],
    "low_price": ["چرا قیمتاتون پایینه", "چرا ارزونه", "چرا قیمت پایین", "چرا انقدر ارزونه"],
    "size": ["چه سایزی", "سایز من", "سایز", "اندازه", "قد و وزن", "چه سایز بگیرم", "اسمال", "مدیوم", "لارج", "ایکس لارج", "دو ایکس", "سه ایکس", "چهار ایکس", "2xl", "3xl", "4xl", "xxl", "xxxl"],
    "shipping_cost": ["هزینه ارسال", "هزینه پست", "پست چنده", "ارسال چنده", "کرایه"],
    "shipping_cheap": ["چرا هزینه پست کمه", "چرا پست ارزونه", "چرا ارسال ارزونه", "هزینه ارسال چرا کمه"],
    "shipping_time": ["چند روزه میرسه", "کی میرسه", "زمان ارسال", "چقدر طول میکشه", "چند روز طول میکشه"],
    "shipping_days": ["چه روزهایی ارسال", "جمعه ارسال", "روز ارسال", "کی ارسال میکنید"],
    "shipping_method": ["تیپاکس", "باربری", "اتوبوس", "ترمینال", "چاپار", "پیک بفرست"],
    "late": ["هنوز نرسیده", "چرا نرسیده", "به دستم نرسیده", "کد رهگیری", "کد ارسالی"],
    "payment": ["شماره کارت", "کارت بده", "پرداخت", "واریز", "چطور پرداخت"],
    "stock": ["موجوده", "موجودی", "دارین", "دارید", "تموم نشده"],
    "color": ["چه رنگی", "رنگ بندی", "رنگبندی", "رنگ دیگه", "مشکی دارین", "سفید دارین"],
    "quality": ["جنسش چیه", "کیفیت", "پارچه", "جنس", "ضخامت", "گرماژ"],
    "original": ["اورجینال", "اصل هست", "فیکه", "اصله", "های کپی"],
    "return": ["مرجوع", "تعویض", "پس بدم", "پس گرفتن", "تعویض سایز"],
}

INTENT_PRIORITY = [
    "wait", "confused", "dont_know", "price_difference", "shipping_method",
    "shipping_cheap", "shipping_cost", "shipping_time", "shipping_days", "late", "low_price",
    "size", "payment", "stock", "color", "quality", "original", "return",
    "order", "price", "greeting", "thanks", "bye"
]

def detect_intent(text):
    n = normalize_text(text)
    if not n:
        return None

    # Structured height/weight or a direct size token should be handled as sizing.
    if ("قد" in n and re.search(r"\d{3}", n)) or ("وزن" in n and re.search(r"\d{2,3}", n)):
        return "size"
    if re.search(r"(?i)(?:^|\s)(?:s|m|l|xl|2xl|3xl|4xl|xxl|xxxl)(?:$|\s)", (text or "").strip()):
        return "size"
    if any(x in n for x in ["اسمال", "مدیوم", "لارج", "ایکس لارج", "دو ایکس", "سه ایکس", "چهار ایکس"]):
        return "size"

    thresholds = {
        "greeting": 0.76,
        "wait": 0.70,
        "confused": 0.68,
        "dont_know": 0.68,
        "price": 0.74,
        "size": 0.72,
    }
    for intent in INTENT_PRIORITY:
        if fuzzy_any(n, INTENTS[intent], thresholds.get(intent, 0.72)):
            return intent
    return None


# ------------------------------------------------------------
# V9 smart understanding layer
# ------------------------------------------------------------

# Extra aliases intentionally focus on how Persian customers actually type:
# short forms, slang, missing نیم‌فاصله, and common spelling mistakes.
SMART_CATEGORY_PHRASES = {
    "price": ["قیمت", "چنده", "چند درمیاد", "قیمط", "قیمتش", "فی", "مبلغ"],
    "discount": ["تخفیف", "تخفیف میدی", "کم نمیکنی", "راه نداره", "آخرش چند", "قیمت آخر", "آف"],
    "last_price": ["قیمت آخر", "آخرش چند", "تهش چند", "آخر قیمت"],
    "wholesale_price": ["عمده", "قیمت عمده", "همکاری", "تعداد بالا قیمت"],
    "stock": ["موجود", "دارین", "دارید", "هست", "تموم", "ناموجود"],
    "restock": ["شارژ میشه", "کی موجود میشه", "دوباره میارین", "شارژ مجدد"],
    "color": ["رنگ", "رنگبندی", "چه رنگ", "مشکی", "سفید", "آبی", "قرمز"],
    "size": ["سایز", "اندازه", "چه سایزی", "سایضم", "سایض", "اسمال", "مدیوم", "لارج", "ایکس لارج", "دو ایکس", "سه ایکس", "چهار ایکس", "xl", "2xl", "3xl", "4xl", "xxl", "xxxl"],
    "height_weight": ["قد", "وزن", "قدم", "وزنم", "قد و وزن"],
    "between_sizes": ["بین دو سایز", "بین لارج و ایکس", "کدوم سایز بهتره"],
    "size_chart": ["جدول سایز", "اندازه ها", "اندازه سایزها", "سایز چارت"],
    "fabric": ["جنس", "پارچه", "جنسش", "چه جنسی"],
    "quality": ["کیفیت", "کیفیته", "خوبه", "جنس خوبه", "دوام"],
    "thickness": ["ضخیم", "نازک", "ضخامت", "گرماژ"],
    "stretch": ["کشی", "کش میاد", "کشسان"],
    "lining": ["کرکی", "داخل کرک", "تو کرک"],
    "warmth": ["گرمه", "گرم", "زمستونی"],
    "shrink": ["آبرفت", "آب میره", "جمع میشه"],
    "colorfast": ["رنگ میده", "رنگ پس میده", "رنگ دهی"],
    "pilling": ["پرز", "پرز میده", "گلوله میشه"],
    "washing": ["شستشو", "بشورم", "ماشین لباسشویی", "چطور بشورم"],
    "original": ["اصل", "اورجینال", "فیک", "های کپی", "اصله"],
    "brand": ["برند", "مارک", "چه مارکی"],
    "country": ["ساخت کجا", "کشور سازنده", "تولید کجا"],
    "photo": ["عکس", "تصویر", "عکسشو"],
    "real_photo": ["عکس واقعی", "عکس خود کار", "عکس رئال"],
    "video": ["ویدیو", "ویدئو", "فیلم", "فیلمشو"],
    "model_photo": ["تنخور", "تن خور", "روی تن", "عکس تن"],
    "order": ["سفارش", "ثبت سفارش", "بخرم", "میخوامش", "خرید"],
    "add_item": ["اضافه کن", "یکی دیگه", "اینم اضافه", "یه کار دیگه"],
    "remove_item": ["حذف کن", "نمیخوامش", "بردارش", "این رو نمیخوام"],
    "edit_order": ["ویرایش", "عوض کنم", "تغییر سفارش", "اشتباه زدم"],
    "cancel": ["لغو", "کنسل", "سفارش نمیخوام", "بیخیال سفارش"],
    "quantity": ["تعداد", "چندتا", "چند تا", "عدد"],
    "cart": ["سبد", "چی سفارش دادم", "لیست سفارشم"],
    "total": ["جمع", "جمع کل", "همش چند", "مجموع"],
    "payment": ["پرداخت", "واریز", "کارت به کارت", "پول"],
    "card": ["شماره کارت", "کارت بده", "شماره حساب"],
    "receipt": ["رسید", "فیش", "عکس واریز"],
    "shipping": ["ارسال", "پست", "فرستادن", "ارسالش"],
    "shipping_fee": ["هزینه پست", "هزینه ارسال", "پست چنده", "کرایه", "هزینه پوصت"],
    "shipping_cheap": ["چرا پست ارزونه", "چرا هزینه پست کمه", "چرا ارسال کمه", "هزینه ارسال چرا پایینه"],
    "shipping_method": ["تیپاکس", "تیباکس", "تیباکث", "چاپار", "باربری", "اتوبوس", "پیک"],
    "shipping_time": ["کی میرسه", "چند روزه", "زمان ارسال", "چقدر طول میکشه"],
    "tracking": ["کد رهگیری", "رهگیری", "ترکینگ", "کد پست"],
    "late_delivery": ["نرسیده", "دیر شده", "چرا نیومده", "هنوز نیومده"],
    "return": ["مرجوع", "پس بدم", "برگردونم"],
    "exchange": ["تعویض", "عوض کنم", "تعویض سایز"],
    "wrong_item": ["اشتباه فرستادین", "محصول اشتباه", "یه چیز دیگه اومده"],
    "damaged": ["خراب", "پاره", "آسیب", "لکه", "ایراد"],
    "trust": ["اعتماد", "معتبر", "مطمئن", "کلاهبرداری", "اسکم"],
    "store_address": ["آدرس مغازه", "آدرس فروشگاه", "حضوری کجایین"],
    "in_person": ["حضوری", "خرید حضوری", "بیام مغازه"],
    "working_hours": ["ساعت کاری", "کی بازین", "چه ساعتی"],
    "recommend": ["پیشنهاد", "چی بخرم", "چی خوبه", "کدوم بهتره"],
    "gift": ["هدیه", "کادو", "برای دوست", "برای شوهر", "برای پسر"],
    "comparison": ["کدوم بهتره", "مقایسه", "فرق این دوتا", "چه فرقی"],
    "wait": ["وایسا", "صبر", "یه لحظه", "الان نه"],
    "confused": ["چی میگی", "چی گفتی", "نفهمیدم", "متوجه نشدم", "منظورت چیه"],
    "dont_know": ["نمیدونم", "نمدونم", "بلد نیستم", "اطلاع ندارم"],
    "thanks": ["مرسی", "ممنون", "دمت گرم", "تشکر"],
    "bye": ["خدافظ", "خداحافظ", "فعلا", "بای"],
}

SMART_TYPO_WORDS = {
    "قیمط":"قیمت", "قیمتشع":"قیمتش", "چنذع":"چنده", "چندع":"چنده",
    "پوصت":"پست", "پوصط":"پست", "تیباکس":"تیپاکس", "تیباکث":"تیپاکس",
    "سایض":"سایز", "سایضم":"سایزم", "نمدونم":"نمیدونم", "نمیدنم":"نمیدونم",
    "میخام":"میخوام", "میخاد":"میخواد", "ادرس":"آدرس", "اورجینل":"اورجینال",
    "موجوذه":"موجوده", "مرجوعیع":"مرجوعی", "رهگیریی":"رهگیری",
}

QUESTIONISH = {
    "price","discount","last_price","wholesale_price","stock","restock","color","size",
    "height_weight","between_sizes","size_chart","fabric","quality","thickness","stretch",
    "lining","warmth","shrink","colorfast","pilling","washing","original","brand","country",
    "photo","real_photo","video","model_photo","shipping","shipping_fee","shipping_method",
    "shipping_time","shipping_cheap","tracking","late_delivery","return","exchange","wrong_item","damaged",
    "trust","store_address","in_person","working_hours","recommend","gift","comparison",
    "payment","card","receipt","total","cart"
}

CATEGORY_TO_CORE = {
    "shipping_fee":"shipping_cost", "shipping":"shipping_time", "tracking":"late",
    "late_delivery":"late", "exchange":"return", "fabric":"quality", "thickness":"quality",
    "stretch":"quality", "lining":"quality", "warmth":"quality", "shrink":"quality",
    "colorfast":"quality", "pilling":"quality", "card":"payment", "receipt":"payment",
    "height_weight":"size", "between_sizes":"size", "size_chart":"size",
}

def smart_normalize(text):
    n = normalize_text(text)
    words = [SMART_TYPO_WORDS.get(w, w) for w in n.split()]
    return " ".join(words)

def looks_like_question(text):
    n = smart_normalize(text)
    if "?" in text or "؟" in text:
        return True
    question_phrases = [
        "چه رنگ", "چه سایز", "می شه", "میخوام بدونم",
        "قیمت", "هزینه", "ارسال", "پست", "تعویض", "مرجوع",
        "اورجینال", "اصله", "فیکه", "چیه", "چطوره",
        "داره", "دارن", "هست", "هستن", "مناسبه", "میاد",
        "میده", "میشه", "خوبه"
    ]
    if any(smart_normalize(q) in n for q in question_phrases):
        return True
    question_tokens = {
        "چند","چقدر","چجوری","چطور","چرا","کی","کجا","کدوم",
        "دارین","دارید","موجوده","میشه","بگین","بگو"
    }
    return any(tok in question_tokens for tok in n.split())

def _phrase_score(n, phrase):
    p = smart_normalize(phrase)
    if not p:
        return 0.0
    words=n.split()
    pwords=p.split()

    # Short one-word aliases (e.g. "قد", "کی") must match a token, not a
    # substring inside unrelated words such as "چقدره" or "مشکی".
    if len(pwords)==1 and len(p)<=4:
        if p in words:
            return 0.95
        best=max([similarity(w,p) for w in words] or [0.0])
        return best*0.90 if best>=0.90 else 0.0

    if p in n:
        return min(1.0, 0.86 + min(len(p), 20) / 150.0)
    nw, pw = set(words), set(pwords)
    overlap = len(nw & pw) / max(1, len(pw))
    seq = similarity(n, p)
    chunks=[]
    plen=max(1,len(pwords))
    for size in range(max(1,plen-1), min(len(words),plen+2)+1):
        chunks += [" ".join(words[i:i+size]) for i in range(len(words)-size+1)]
    local=max([similarity(c,p) for c in chunks] or [0.0])
    return max(overlap*0.88, seq*0.72, local*0.92)

def detect_categories(text, limit=5):
    n = smart_normalize(text)
    if not n:
        return []
    scored=[]
    for category, phrases in SMART_CATEGORY_PHRASES.items():
        score=max((_phrase_score(n,p) for p in phrases), default=0)
        threshold = 0.70 if category in {"wait","confused","dont_know"} else 0.74
        if score >= threshold:
            scored.append((category, score))
    scored.sort(key=lambda x:(-x[1], -max((len(p) for p in SMART_CATEGORY_PHRASES[x[0]]),default=0)))
    # Avoid near-duplicate categories in the same answer.
    out=[]
    for cat,score in scored:
        if cat not in out:
            out.append(cat)
        if len(out)>=limit:
            break
    return out

def detect_core_intents(text):
    """Return more than one core intent when the customer asks several questions."""
    cats=detect_categories(text, limit=8)
    cores=[]
    for cat in cats:
        core=CATEGORY_TO_CORE.get(cat, cat)
        if core in INTENTS and core not in cores:
            cores.append(core)
    fallback=detect_intent(text)
    if fallback and fallback not in cores:
        cores.append(fallback)
    return cores

def bank_answer(category):
    pool=RESPONSES.get(category)
    if not pool:
        pool=RESPONSES.get("unclear") or RESPONSES.get("confused") or UNKNOWN_REPLIES
    return random.choice(pool)

def answer_category(category, text, chat_id):
    core=CATEGORY_TO_CORE.get(category, category)
    if core in INTENTS:
        ans=answer_intent(core, text, chat_id)
        if ans:
            return ans
    # Long-tail categories use the corresponding 100K bank category. These are
    # deliberately non-committal when store-specific facts are unknown.
    return bank_answer(category)

def multi_question_answer(text, chat_id, max_answers=3):
    n = normalize_text(text)
    # Do not mistake several fuzzy category hits for several questions.
    # Require an actual conjunction or multiple question marks before composing
    # a multi-part answer.
    conjunctions = len(re.findall(r"(?:^|\s)و(?:\s|$)", n))
    qmarks = (text or "").count("?") + (text or "").count("؟")
    if conjunctions < 1 and qmarks < 2:
        return None
    cats=[c for c in detect_categories(text, limit=8) if c in QUESTIONISH]
    # Remove semantically overlapping answers.
    chosen=[]
    seen_core=set()
    for c in cats:
        core=CATEGORY_TO_CORE.get(c,c)
        group = core if core in INTENTS else c
        if group in seen_core:
            continue
        seen_core.add(group)
        chosen.append(c)
        if len(chosen)>=max_answers:
            break
    if len(chosen)<2:
        return None
    parts=[]
    for c in chosen:
        a=answer_category(c,text,chat_id)
        if a:
            parts.append("• "+a)
    return "\n\n".join(parts) if len(parts)>=2 else None

# ------------------------------------------------------------
# Small talk / response composition
# ------------------------------------------------------------

def compose(body, close=True):
    opener = random.choice(FRIENDLY_OPENERS)
    closer = random.choice(SOFT_CLOSERS) if close else ""
    parts = [opener, body]
    if closer:
        parts.append(closer)
    return " ".join(p for p in parts if p).strip()

def state_explanation(state):
    mapping = {
        "await_product_count": "فقط می‌خوام بدونم چند محصول می‌خوای. مثلاً بنویس «3». اگه چندتا از یک مدل می‌خوای می‌تونی بنویسی «5 تا هودی مشکی».",
        "await_item_name": "دارم محصول‌های سفارشت رو یکی‌یکی ثبت می‌کنم. فقط اسم محصولی که الان می‌خوای اضافه بشه رو بفرست.",
        "confirm_cart": "لیست محصولات رو بستیم؛ فقط می‌خوام بدونم محصول دیگه‌ای اضافه می‌کنی یا همین‌ها نهایی بشن.",
        "await_add_count": "گفتی محصول بیشتری می‌خوای؛ فقط تعداد محصول‌های جدید رو بگو.",
        "await_size": "الان فقط سایز هر محصول رو لازم دارم. اگه سایزت رو نمی‌دونی، قد و وزنت رو بفرست تا راهنماییت کنم.",
        "await_height_weight": "سایزت رو با قد و وزن حدودی پیشنهاد می‌دم. مثلاً بنویس «قد 180 وزن 80، فیت معمولی».",
        "await_name": "برای ثبت سفارش فقط اسم و فامیلی تحویل‌گیرنده رو لازم دارم.",
        "await_phone": "شماره موبایل گیرنده رو برای اطلاعات سفارش و ارسال لازم دارم؛ مثل 09123456789.",
        "await_address": "الان آدرس ارسال رو لازم دارم؛ شهر، خیابون و پلاک رو بنویس. کدپستی اگر داری بهتره.",
        "confirm_order": "همه اطلاعات آماده است؛ فقط تأیید نهایی، ویرایش یا کنسل‌کردن سفارش مونده.",
        "confirm_cancel": "برای امنیت سفارش منتظر تأیید تو هستم؛ فقط بگو «بله، کنسل کن» یا «نه».",
        "edit_menu": "داریم سفارش رو ویرایش می‌کنیم؛ بخش موردنظر رو از فهرست انتخاب کن.",
        "await_receipt": "سفارش ثبت شده و الان منتظر عکس رسید واریز هستم. اگه سوالی داری قبلش بپرس.",
    }
    return mapping.get(state, "بگو دقیقاً کدوم بخش رو می‌خوای توضیح بدم تا ساده بگم.")

def resume_prompt(state, chat_id):
    c = get_chat(chat_id)
    if state == "await_product_count":
        return "خب، برای ادامه فقط تعداد محصول رو بفرست؛ بین ۱ تا ۵۰."
    if state == "await_item_name":
        current = int(c["collected_items"] or 0) + 1
        expected = int(c["expected_items"] or 1)
        return f"برای ادامه اسم محصول شماره {current} از {expected} رو بفرست."
    if state == "confirm_cart":
        return "برای ادامه بنویس «همین‌ها» یا «اضافه»."
    if state == "await_add_count":
        remaining = MAX_ITEMS_PER_ORDER - cart_unit_count(chat_id)
        return f"برای ادامه تعداد محصول‌های جدید رو بگو؛ حداکثر {remaining} عدد."
    if state == "await_size":
        return size_request_prompt(chat_id, "برای ادامه")
    if state == "await_height_weight":
        return "قد و وزنت رو بفرست؛ مثلاً «قد 180 وزن 80»."
    if state == "await_name":
        return "برای ادامه اسم و فامیلی تحویل‌گیرنده رو بفرست."
    if state == "await_phone":
        return "برای ادامه شماره موبایل گیرنده رو بفرست."
    if state == "await_address":
        return "برای ادامه آدرس کامل ارسال رو بفرست."
    if state == "confirm_order":
        return "برای ادامه بنویس «تأیید نهایی» یا «ویرایش سفارش»."
    if state == "confirm_cancel":
        return "برای کنسل‌شدن کامل سفارش بنویس «بله»؛ برای برگشت بنویس «نه»."
    if state == "edit_menu":
        return edit_menu_text()
    if state == "await_receipt":
        return "هر وقت واریز کردی، عکس رسید رو همینجا بفرست."
    return ""

# ------------------------------------------------------------
# Size recommendation
# ------------------------------------------------------------

def extract_height_weight(text):
    """Extract plausible height/weight values from casual Persian messages."""
    n = normalize_text(text)
    height = None
    weight = None

    mh = re.search(r"(?:قد|قدم)\s*[:\-]?\s*(1\d{2}|20\d|21\d)", n)
    mw = re.search(r"(?:وزن|وزنم)\s*[:\-]?\s*(\d{2,3})", n)
    if mh:
        height = int(mh.group(1))
    if mw:
        weight = int(mw.group(1))

    nums = [int(x) for x in re.findall(r"\b\d{2,3}\b", n)]
    if height is None:
        h_candidates = [x for x in nums if 140 <= x <= 215]
        if h_candidates:
            height = h_candidates[0]
    if weight is None:
        w_candidates = [x for x in nums if 40 <= x <= 180 and x != height]
        if w_candidates:
            weight = w_candidates[0]
    return height, weight


def detect_fit(text):
    n = normalize_text(text)
    if fuzzy_any(n, ["خیلی آزاد", "اورسایز", "لش", "گشاد", "آزاد"], 0.72):
        return "loose"
    if fuzzy_any(n, ["جذب", "چسبان", "فیت بدن", "تنگ"], 0.72):
        return "slim"
    return "regular"


SIZE_ORDER = ["S", "M", "L", "XL", "2XL", "3XL", "4XL"]
SIZE_LABEL_FA = {
    "S": "اسمال", "M": "مدیوم", "L": "لارج", "XL": "ایکس‌لارج",
    "2XL": "دو ایکس‌لارج", "3XL": "سه ایکس‌لارج", "4XL": "چهار ایکس‌لارج",
}


def shift_size(size, delta):
    try:
        i = SIZE_ORDER.index(size)
    except ValueError:
        return size
    return SIZE_ORDER[max(0, min(len(SIZE_ORDER)-1, i+delta))]


def extract_explicit_size(text):
    """Understand Latin and common Persian ways customers name a size.

    Numeric sizes are matched deterministically (not fuzzily) so 2XL/3XL/4XL
    can never be confused with one another.
    """
    raw = unicodedata.normalize("NFKC", text or "").upper().replace(" ", "")
    patterns = [
        (r"4XL|XXXXL", "4XL"),
        (r"3XL|XXXL", "3XL"),
        (r"2XL|XXL", "2XL"),
        (r"XL", "XL"),
    ]
    for pat, code in patterns:
        if re.search(pat, raw):
            return code

    n = normalize_text(text)
    # Persian multi-word aliases: exact containment is safer than fuzzy matching.
    exact_aliases = [
        (["چهار ایکس لارج", "4 ایکس لارج", "چهار ایکس", "فور ایکس"], "4XL"),
        (["سه ایکس لارج", "3 ایکس لارج", "سه ایکس", "تری ایکس"], "3XL"),
        (["دو ایکس لارج", "2 ایکس لارج", "دو ایکس", "ایکس ایکس لارج"], "2XL"),
        (["ایکس لارج", "اکس لارج"], "XL"),
    ]
    for phrases, code in exact_aliases:
        if any(normalize_text(ph) in n for ph in phrases):
            return code

    # Single-letter Latin sizes should be token-aware and checked last.
    raw_spaced = unicodedata.normalize("NFKC", text or "").upper()
    for code in ("L", "M", "S"):
        if re.search(rf"(?<![A-Z]){code}(?![A-Z])", raw_spaced):
            return code

    # Persian size names must be explicit words/phrases. Never fuzzy-match short
    # customer words such as «اسم» to «اسمال».
    simple_aliases = [
        (["لارج"], "L"),
        (["مدیوم"], "M"),
        (["اسمال", "اسمول"], "S"),
    ]
    for phrases, code in simple_aliases:
        if any(re.search(rf"(?:^|\s){re.escape(normalize_text(ph))}(?:$|\s)", n) for ph in phrases):
            return code
    return None


def detect_product_type(text):
    n = normalize_text(text)
    if fuzzy_any(n, ["هودی", "دورس", "سویشرت"], 0.78):
        return "outerwear"
    if fuzzy_any(n, ["تیشرت", "تی شرت", "پولوشرت", "پیراهن"], 0.78):
        return "top"
    if fuzzy_any(n, ["شلوار", "اسلش", "جاگر"], 0.78):
        return "bottom"
    return "generic"


def recommend_size(height, weight, fit="regular", product_type="generic"):
    """Conservative conversational estimate for S..4XL.

    Weight drives the base size; height and garment/fitting preferences make small
    adjustments. It is intentionally advisory because actual garment measurements
    can vary between patterns.
    """
    # Broad adult menswear heuristic; not a substitute for garment measurements.
    if weight < 55:
        size = "S"
    elif weight < 65:
        size = "M"
    elif weight < 75:
        size = "L"
    elif weight < 88:
        size = "XL"
    elif weight < 102:
        size = "2XL"
    elif weight < 118:
        size = "3XL"
    else:
        size = "4XL"

    # Height can change torso/sleeve length needs, but should not dominate weight.
    if height >= 190 and weight >= 70:
        size = shift_size(size, 1)
    elif height <= 162 and weight < 70:
        size = shift_size(size, -1)

    # Hoodies/sweatshirts are often preferred with a little more ease.
    if product_type == "outerwear" and fit == "loose":
        size = shift_size(size, 1)
    elif fit == "loose":
        size = shift_size(size, 1)
    elif fit == "slim":
        size = shift_size(size, -1)
    return size


def size_answer(text):
    explicit = extract_explicit_size(text)
    h, w = extract_height_weight(text)

    # A direct stock/size statement such as "من دو ایکس لارجم" should be understood.
    if explicit and not (h and w):
        return (
            f"آره عزیز 🌹 سایز {explicit} ({SIZE_LABEL_FA[explicit]}) موجوده ✅ "
            "سایزبندی کامل ما از S تا 4XL هست. اگه قد و وزنت رو هم بگی می‌تونم بگم همین سایز برای فیتی که دوست داری مناسبه یا بهتره یک سایز بالا/پایین برداری.",
            explicit,
        )

    if not h or not w:
        return random.choice(SIZE_ASK_REPLIES), None
    if not (140 <= h <= 215 and 40 <= w <= 180):
        return "قد یا وزن رو درست متوجه نشدم. مثلاً بنویس «قد 180 وزن 80». 🌹", None

    fit = detect_fit(text)
    product_type = detect_product_type(text)
    size = recommend_size(h, w, fit, product_type)
    fit_fa = {"loose": "آزاد/اورسایز", "slim": "جذب‌تر", "regular": "معمولی"}[fit]

    stated_note = ""
    if explicit:
        distance = abs(SIZE_ORDER.index(explicit) - SIZE_ORDER.index(size))
        if explicit == size:
            stated_note = f" سایزی که خودت گفتی ({explicit}) هم با این پیشنهاد هماهنگه ✅"
        elif distance == 1:
            stated_note = f" سایز {explicit} که گفتی هم نزدیکه؛ انتخاب بین {size} و {explicit} بیشتر به آزاد یا جذب پوشیدن بستگی داره."
        else:
            stated_note = f" تو {explicit} رو گفتی؛ با این قد و وزن من {size} رو تقریبی‌تر می‌بینم، پس برای تصمیم قطعی اندازه دور سینه یا اندازه لباس فعلیت خیلی کمک می‌کنه."

    neighbor = shift_size(size, 1)
    extra = ""
    if fit == "regular" and neighbor != size:
        extra = f" اگر بین دو سایز مرددی یا لباس رو آزادتر دوست داری، {neighbor} هم می‌تونه انتخاب راحت‌تری باشه."

    body = (
        f"با قد {h} و وزن {w}، برای فیت {fit_fa} پیشنهاد من {size} هست 👌"
        f"{stated_note}{extra}"
    )
    return body, size

# ------------------------------------------------------------
# Database
# ------------------------------------------------------------

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
            misunderstood_count INTEGER DEFAULT 0,
            previous_state TEXT DEFAULT '',
            edit_target INTEGER DEFAULT 0,
            pending_size TEXT DEFAULT ''
        )
    """)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(chats)").fetchall()}
    migrations = {
        "expected_items": "INTEGER DEFAULT 0",
        "collected_items": "INTEGER DEFAULT 0",
        "misunderstood_count": "INTEGER DEFAULT 0",
        "previous_state": "TEXT DEFAULT ''",
        "edit_target": "INTEGER DEFAULT 0",
        "pending_size": "TEXT DEFAULT ''",
    }
    for col, spec in migrations.items():
        if col not in cols:
            conn.execute(f"ALTER TABLE chats ADD COLUMN {col} {spec}")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS cart_items(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            price INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            size TEXT DEFAULT ''
        )
    """)
    cart_cols = {row[1] for row in conn.execute("PRAGMA table_info(cart_items)").fetchall()}
    if "quantity" not in cart_cols:
        conn.execute("ALTER TABLE cart_items ADD COLUMN quantity INTEGER DEFAULT 1")
    if "size" not in cart_cols:
        conn.execute("ALTER TABLE cart_items ADD COLUMN size TEXT DEFAULT ''")

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
            quantity INTEGER DEFAULT 1,
            size TEXT DEFAULT ''
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS card_messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_connection_id TEXT NOT NULL,
            chat_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            card_snapshot TEXT,
            created_at TEXT NOT NULL,
            deleted_at TEXT,
            UNIQUE(business_connection_id, chat_id, message_id)
        )
    """)
    oi_cols = {row[1] for row in conn.execute("PRAGMA table_info(order_items)").fetchall()}
    if "quantity" not in oi_cols:
        conn.execute("ALTER TABLE order_items ADD COLUMN quantity INTEGER DEFAULT 1")
    if "size" not in oi_cols:
        conn.execute("ALTER TABLE order_items ADD COLUMN size TEXT DEFAULT ''")

    conn.commit()
    conn.close()

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

def ensure_chat(chat_id, connection_id):
    conn = db()
    conn.execute(
        "INSERT INTO chats(chat_id,connection_id) VALUES(?,?) "
        "ON CONFLICT(chat_id) DO UPDATE SET connection_id=excluded.connection_id",
        (chat_id, connection_id)
    )
    conn.commit()
    conn.close()

def get_chat(chat_id):
    conn = db()
    row = conn.execute("SELECT * FROM chats WHERE chat_id=?", (chat_id,)).fetchone()
    conn.close()
    return row

def update_chat(chat_id, **kwargs):
    if not kwargs:
        return
    conn = db()
    fields = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [chat_id]
    conn.execute(f"UPDATE chats SET {fields} WHERE chat_id=?", vals)
    conn.commit()
    conn.close()

# ------------------------------------------------------------
# Telegram API
# ------------------------------------------------------------

def api(method, data=None):
    r = requests.post(f"{API}/{method}", data=data or {}, timeout=65)
    r.raise_for_status()
    payload = r.json()
    if not payload.get("ok"):
        raise RuntimeError(payload)
    return payload["result"]

def _extract_card_number_from_text(text):
    if not text:
        return ""
    # Accept digits separated by spaces/dashes while avoiding unrelated long numbers.
    for candidate in re.findall(r"(?:\d[ -]?){16}", str(text)):
        digits = re.sub(r"\D", "", candidate)
        if len(digits) == 16:
            return digits
    return ""

def _remember_card_message(connection_id, chat_id, result, text):
    if not isinstance(result, dict):
        return
    message_id = result.get("message_id")
    if not message_id:
        return
    card = _extract_card_number_from_text(text)
    if not card or "کارت" not in normalize_text(text):
        return
    conn = db()
    conn.execute(
        "INSERT OR IGNORE INTO card_messages("
        "business_connection_id,chat_id,message_id,card_snapshot,created_at"
        ") VALUES(?,?,?,?,?)",
        (str(connection_id), int(chat_id), int(message_id), card, datetime.now().isoformat(timespec="seconds"))
    )
    conn.commit()
    conn.close()

def send_business(connection_id, chat_id, text):
    result = api("sendMessage", {
        "business_connection_id": connection_id,
        "chat_id": chat_id,
        "text": text,
    })
    _remember_card_message(connection_id, chat_id, result, text)
    return result

def delete_tracked_card_messages():
    conn = db()
    rows = conn.execute(
        "SELECT id,business_connection_id,chat_id,message_id "
        "FROM card_messages WHERE deleted_at IS NULL ORDER BY id"
    ).fetchall()
    conn.close()

    if not rows:
        return 0, 0, 0

    groups = {}
    for row in rows:
        key = (row["business_connection_id"], int(row["chat_id"]))
        groups.setdefault(key, []).append(row)

    deleted = 0
    failed = 0
    for (connection_id, chat_id), group in groups.items():
        for start in range(0, len(group), 100):
            chunk = group[start:start + 100]
            ids = [int(r["message_id"]) for r in chunk]
            try:
                api("deleteBusinessMessages", {
                    "business_connection_id": connection_id,
                    "message_ids": json.dumps(ids),
                })
                now = datetime.now().isoformat(timespec="seconds")
                conn = db()
                conn.executemany(
                    "UPDATE card_messages SET deleted_at=? WHERE id=?",
                    [(now, int(r["id"])) for r in chunk]
                )
                conn.commit()
                conn.close()
                deleted += len(chunk)
            except Exception as exc:
                print(f"Card message delete failed chat={chat_id} ids={ids}: {exc!r}", flush=True)
                failed += len(chunk)
    return deleted, failed, len(rows)

def send_admin(text):
    if ADMIN_ID:
        return api("sendMessage", {"chat_id": ADMIN_ID, "text": text})

def send_admin_photo(file_id, caption):
    if ADMIN_ID:
        return api("sendPhoto", {
            "chat_id": ADMIN_ID,
            "photo": file_id,
            "caption": caption[:1024],
        })

# ------------------------------------------------------------
# Shop utilities
# ------------------------------------------------------------

def fmt_price(n):
    return f"{int(n):,}".replace(",", "٬") + " تومان"

def random_price():
    n = random.randrange(PRICE_MIN // 10_000, PRICE_MAX // 10_000 + 1) * 10_000
    return min(max(n, PRICE_MIN), PRICE_MAX)

def normalize_product_name(name):
    t = normalize_text(name)
    # remove quantity boilerplate so "3 تا هودی" and "هودی" share the same price
    t = re.sub(r"^\d+\s*(?:تا|عدد|دونه|دانه)\s*(?:از\s+)?", "", t).strip()
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
        "SELECT position,product_name,price,COALESCE(quantity,1) AS quantity,COALESCE(size,'') AS size "
        "FROM cart_items WHERE chat_id=? ORDER BY position",
        (chat_id,)
    ).fetchall()
    conn.close()
    return rows

def cart_unit_count(chat_id):
    return sum(int(r["quantity"]) for r in cart_items(chat_id))

def add_cart_item(chat_id, product_name, quantity=1):
    quantity = max(1, int(quantity))
    if cart_unit_count(chat_id) + quantity > MAX_ITEMS_PER_ORDER:
        return None
    position = len(cart_items(chat_id)) + 1
    price = get_or_create_product_price(chat_id, product_name)
    conn = db()
    conn.execute(
        "INSERT INTO cart_items(chat_id,position,product_name,price,quantity,size) VALUES(?,?,?,?,?,'')",
        (chat_id, position, product_name.strip(), price, quantity)
    )
    conn.commit()
    conn.close()
    update_chat(chat_id, collected_items=position)
    return position, price, quantity


def cart_item(chat_id, position):
    return next((r for r in cart_items(chat_id) if int(r["position"]) == int(position)), None)


def next_unsized_cart_item(chat_id):
    return next((r for r in cart_items(chat_id) if not r["size"]), None)


def set_cart_item_size(chat_id, position, size):
    conn = db()
    conn.execute(
        "UPDATE cart_items SET size=? WHERE chat_id=? AND position=?",
        (size, chat_id, int(position)),
    )
    conn.commit()
    conn.close()


def sync_chat_size_summary(chat_id):
    parts = [f"{r['product_name']}: {r['size']}" for r in cart_items(chat_id) if r["size"]]
    update_chat(chat_id, size=" | ".join(parts))


def size_request_prompt(chat_id, prefix=""):
    item = next_unsized_cart_item(chat_id)
    if not item:
        return (prefix + " " if prefix else "") + "همه سایزها ثبت شدن ✅ حالا اسم و فامیلی تحویل‌گیرنده رو بفرست."
    qty = int(item["quantity"])
    qty_text = f" برای هر {qty} عدد" if qty > 1 else ""
    lead = (prefix + "\n\n") if prefix else ""
    return (
        f"{lead}سایز «{item['product_name']}»{qty_text} رو بگو؛ "
        "S، M، L، XL، 2XL، 3XL یا 4XL. اگر نمی‌دونی بنویس «نمیدونم»."
    )


def save_current_product_size(chat_id, size):
    item = next_unsized_cart_item(chat_id)
    if not item:
        update_chat(chat_id, size=size, state="await_name", pending_size="")
        return None
    set_cart_item_size(chat_id, item["position"], size)
    sync_chat_size_summary(chat_id)
    update_chat(chat_id, pending_size="")
    next_item = next_unsized_cart_item(chat_id)
    if not next_item:
        update_chat(chat_id, state="await_name")
    return next_item


def numbered_cart(chat_id):
    rows = cart_items(chat_id)
    if not rows:
        return "سبد سفارش خالیه."
    return "\n".join(
        f"{r['position']}) {r['product_name']} × {r['quantity']}"
        + (f" — سایز {r['size']}" if r["size"] else "")
        for r in rows
    )


def delete_cart_item(chat_id, position):
    conn = db()
    cur = conn.execute(
        "DELETE FROM cart_items WHERE chat_id=? AND position=?", (chat_id, int(position))
    )
    if cur.rowcount:
        rows = conn.execute(
            "SELECT id FROM cart_items WHERE chat_id=? ORDER BY position", (chat_id,)
        ).fetchall()
        for new_position, row in enumerate(rows, 1):
            conn.execute("UPDATE cart_items SET position=? WHERE id=?", (new_position, row["id"]))
    conn.commit()
    conn.close()
    if cur.rowcount:
        update_chat(chat_id, collected_items=len(cart_items(chat_id)))
        sync_chat_size_summary(chat_id)
    return bool(cur.rowcount)


def update_cart_quantity(chat_id, position, quantity):
    item = cart_item(chat_id, position)
    if not item:
        return False, "محصول پیدا نشد."
    quantity = int(quantity)
    if quantity < 1:
        return False, "تعداد باید حداقل ۱ باشه."
    new_total = cart_unit_count(chat_id) - int(item["quantity"]) + quantity
    if new_total > MAX_ITEMS_PER_ORDER:
        return False, "جمع تعداد محصولات نباید بیشتر از ۵۰ تا بشه."
    conn = db()
    conn.execute(
        "UPDATE cart_items SET quantity=? WHERE chat_id=? AND position=?",
        (quantity, chat_id, int(position)),
    )
    conn.commit()
    conn.close()
    return True, ""

def cart_subtotal(chat_id):
    return sum(int(r["price"]) * int(r["quantity"]) for r in cart_items(chat_id))

def cart_total(chat_id):
    return cart_subtotal(chat_id) + (SHIPPING_FEE if cart_items(chat_id) else 0)

def cart_summary(chat_id):
    rows = cart_items(chat_id)
    if not rows:
        return "سبد سفارش خالیه."
    lines = ["🛍 سفارش تا اینجا:"]
    for r in rows:
        qty = int(r["quantity"])
        unit = int(r["price"])
        size_text = f" | سایز {r['size']}" if r["size"] else ""
        if qty == 1:
            lines.append(f"• {r['product_name']}{size_text} — حدود {fmt_price(unit)}")
        else:
            lines.append(
                f"• {r['product_name']} × {qty}{size_text} — هر عدد حدود {fmt_price(unit)} "
                f"(جمع {fmt_price(unit * qty)})"
            )
    lines.append("")
    lines.append(f"جمع محصولات: {fmt_price(cart_subtotal(chat_id))}")
    lines.append(f"پست پیشتاز: {fmt_price(SHIPPING_FEE)}")
    lines.append(f"جمع کل: {fmt_price(cart_total(chat_id))}")
    return "\n".join(lines)


def looks_like_product_reference(text):
    raw = (text or "").strip()
    n = normalize_text(raw)
    if not n:
        return False
    if re.search(r"https?://|t\.me/|instagram\.com/", raw, re.I):
        return True
    product_words = {
        "هودی", "دورس", "تیشرت", "تی شرت", "شلوار", "ست", "پیراهن",
        "کاپشن", "سویشرت", "بلوز", "پولوشرت", "کت", "شورت", "لباس"
    }
    if not any(w in n for w in product_words):
        return False
    # A short product/model mention should be treated as a product reference,
    # but real questions such as "هودی چه سایزیه؟" should go to intent handling.
    return not looks_like_question(raw)

def parse_count(text):
    n = normalize_text(text)
    m = re.search(r"\d+", n)
    return int(m.group()) if m else None

def parse_quantity_product(text):
    n = (text or "").translate(PERSIAN_DIGITS).strip()
    m = re.match(r"^\s*(\d+)\s*(?:تا|عدد|دونه|دانه)\s*(?:از\s+)?(.+?)\s*$", n)
    if not m:
        return None, None
    return int(m.group(1)), m.group(2).strip()

def extract_phone(text):
    n = (text or "").translate(PERSIAN_DIGITS)
    digits = re.sub(r"\D", "", n)
    if digits.startswith("98") and len(digits) == 12:
        digits = "0" + digits[2:]
    if re.fullmatch(r"09\d{9}", digits):
        return digits
    return ""

def is_done_choice(text):
    n = normalize_text(text)
    phrases = [
        "همین ها", "همینا", "همیناست", "همین", "همین کافیه", "کافیه",
        "تموم", "تمام", "تمومه", "دیگه ندارم", "دیگه نمیخوام", "چیزی نمیخوام",
        "محصول دیگه نمیخوام", "اضافه نمیخوام", "نهایی", "نهایی کن",
        "نه", "خیر", "نمیخوام", "نمی خوام", "کلا نمیخوام", "نمیخوام میگم"
    ]
    if n in {normalize_text(x) for x in phrases}:
        return True
    return any(normalize_text(x) in n for x in ["دیگه نمیخوام", "محصول دیگه نمیخوام", "چیزی اضافه نمیخوام", "همین کافیه", "نهایی کن"])

def is_add_choice(text):
    return fuzzy_any(text, ["اضافه", "بیشتر", "بازم", "یکی دیگه", "محصول دیگه"], 0.68)


def is_cancel_order_request(text):
    """Detect only explicit whole-order cancellation requests.

    Short answers such as «نه» and «نمیخوام» keep their existing meaning in
    cart confirmation and must not cancel the entire checkout accidentally.
    """
    n = normalize_text(text)
    if not n:
        return False
    exact = {
        "لغو", "کنسل", "لغو سفارش", "کنسل سفارش", "لغوش کن", "کنسلش کن",
        "سفارشمو لغو کن", "سفارشم رو لغو کن",
        "سفارشمو کنسل کن", "سفارشم رو کنسل کن",
        "بیخیال سفارش", "از سفارش منصرف شدم", "از خریدم منصرف شدم",
        "کلا سفارش نمیخوام", "دیگه سفارش نمیخوام", "نمیخوام سفارش بدم",
    }
    if n in {normalize_text(x) for x in exact}:
        return True
    cancel_words = ("لغو", "کنسل", "منصرف", "بیخیال")
    order_words = ("سفارش", "سفارشم", "سفارشمو", "خرید", "خریدم")
    action_words = {"کن", "کنید", "میکنم", "میخوام", "شدم", "بشه"}
    tokens = set(n.split())
    return (
        any(word in n for word in cancel_words)
        and any(word in n for word in order_words)
        and bool(tokens & action_words)
    )


def is_yes_choice(text):
    n = normalize_text(text)
    return n in {"بله", "آره", "اره", "اوکی", "تایید", "تأیید", "مطمئنم", "انجامش بده"}


def is_no_choice(text):
    n = normalize_text(text)
    return n in {"نه", "خیر", "نخیر", "نکن", "بیخیال", "لغو نکن", "کنسل نکن"}


def edit_request_kind(text):
    n = normalize_text(text)
    edit_words = ("ویرایش", "تغییر", "عوض", "اصلاح", "اشتباه")
    remove_words = ("حذف", "بردار", "نمیخوامش")
    if any(word in n for word in remove_words) and any(word in n for word in ("محصول", "لباس", "هودی", "تیشرت", "شلوار", "این")):
        return "remove"
    if not any(word in n for word in edit_words):
        return None
    if any(word in n for word in ("آدرس", "ادرس")):
        return "address"
    if any(word in n for word in ("شماره", "موبایل", "تلفن")):
        return "phone"
    if "سایز" in n:
        return "size"
    if any(word in n for word in ("تعداد", "چندتا", "چند تا")):
        return "quantity"
    if any(word in n for word in ("اسم", "نام")):
        return "name"
    if any(word in n for word in ("سفارش", "سفارشم", "خرید")) or n in {"ویرایش", "تغییرش بده", "اشتباه زدم"}:
        return "menu"
    return None


def edit_menu_text():
    return (
        "کدوم بخش سفارش رو می‌خوای ویرایش کنی؟ 🌹\n"
        "1) حذف محصول\n2) تغییر تعداد\n3) تغییر سایز\n"
        "4) تغییر نام گیرنده\n5) تغییر شماره موبایل\n6) تغییر آدرس\n"
        "شماره گزینه یا اسم بخش رو بفرست."
    )


def edit_menu_choice(text):
    n = normalize_text(text)
    direct = {"1":"remove", "2":"quantity", "3":"size", "4":"name", "5":"phone", "6":"address"}
    if n in direct:
        return direct[n]
    if "حذف" in n or "بردار" in n:
        return "remove"
    if "تعداد" in n:
        return "quantity"
    if "سایز" in n:
        return "size"
    if "اسم" in n or "نام" in n:
        return "name"
    if "شماره" in n or "موبایل" in n:
        return "phone"
    if "آدرس" in n or "ادرس" in n:
        return "address"
    return None


def begin_edit(chat_id, current_state, kind="menu"):
    update_chat(chat_id, previous_state=current_state, edit_target=0, pending_size="")
    if kind == "name":
        update_chat(chat_id, state="edit_name")
        return "اسم و فامیلی جدید گیرنده رو بفرست."
    if kind == "phone":
        update_chat(chat_id, state="edit_phone")
        return "شماره موبایل جدید گیرنده رو بفرست."
    if kind == "address":
        update_chat(chat_id, state="edit_address")
        return "آدرس کامل جدید رو بفرست؛ شهر، خیابون و پلاک."
    if kind in {"remove", "quantity", "size"}:
        state_map = {
            "remove":"edit_remove", "quantity":"edit_quantity_target", "size":"edit_size_target"
        }
        action = {"remove":"حذف", "quantity":"تغییر تعداد", "size":"تغییر سایز"}[kind]
        update_chat(chat_id, state=state_map[kind])
        return f"شماره محصولی که می‌خوای {action} بدی رو بفرست:\n{numbered_cart(chat_id)}"
    update_chat(chat_id, state="edit_menu")
    return edit_menu_text()


def finish_edit(chat_id):
    c = get_chat(chat_id)
    target_state = c["previous_state"] or "confirm_order"
    if not cart_items(chat_id):
        target_state = "await_product_count"
    update_chat(chat_id, state=target_state, previous_state="", edit_target=0, pending_size="")
    return target_state


def order_review_text(chat_id, heading="لطفاً سفارش رو یک بار بررسی کن 👇"):
    c = get_chat(chat_id)
    return (
        f"{heading}\n\n{cart_summary(chat_id)}\n\n"
        f"نام گیرنده: {c['full_name']}\n"
        f"موبایل: {c['phone']}\n"
        f"آدرس: {c['address']}\n\n"
        "اگر همه‌چیز درسته بنویس «تأیید نهایی». برای تغییر بنویس «ویرایش سفارش»؛ "
        "برای لغو هم بنویس «کنسل سفارش»."
    )


def edit_done_text(chat_id, detail):
    restored = finish_edit(chat_id)
    if restored == "confirm_order":
        return order_review_text(chat_id, detail + " ✅ حالا دوباره بررسی کن:")
    return detail + " ✅\n\n" + resume_prompt(restored, chat_id)


def process_edit_state(chat_id, state, text):
    """Return (handled, reply) for the small, isolated order-edit state machine."""
    if state == "edit_menu":
        choice = edit_menu_choice(text)
        if not choice:
            return True, edit_menu_text()
        previous = get_chat(chat_id)["previous_state"] or "confirm_order"
        # Keep the original resume target while changing edit sub-states.
        if choice in {"name", "phone", "address"}:
            state_map = {"name":"edit_name", "phone":"edit_phone", "address":"edit_address"}
            prompts = {
                "name":"اسم و فامیلی جدید گیرنده رو بفرست.",
                "phone":"شماره موبایل جدید گیرنده رو بفرست.",
                "address":"آدرس کامل جدید رو بفرست؛ شهر، خیابون و پلاک.",
            }
            update_chat(chat_id, state=state_map[choice], previous_state=previous)
            return True, prompts[choice]
        state_map = {"remove":"edit_remove", "quantity":"edit_quantity_target", "size":"edit_size_target"}
        action = {"remove":"حذف", "quantity":"تغییر تعداد", "size":"تغییر سایز"}[choice]
        update_chat(chat_id, state=state_map[choice], previous_state=previous)
        return True, f"شماره محصولی که می‌خوای {action} بدی رو بفرست:\n{numbered_cart(chat_id)}"

    if state in {"edit_remove", "edit_quantity_target", "edit_size_target"}:
        position = parse_count(text)
        item = cart_item(chat_id, position) if position is not None else None
        if not item:
            return True, "شماره محصول درست نبود. یکی از شماره‌های این لیست رو بفرست:\n" + numbered_cart(chat_id)
        if state == "edit_remove":
            name = item["product_name"]
            delete_cart_item(chat_id, position)
            return True, edit_done_text(chat_id, f"«{name}» از سفارش حذف شد")
        next_state = "edit_quantity_value" if state == "edit_quantity_target" else "edit_size_value"
        update_chat(chat_id, state=next_state, edit_target=int(position))
        prompt = "تعداد جدید رو با عدد بفرست." if next_state == "edit_quantity_value" else "سایز جدید رو بفرست؛ S تا 4XL."
        return True, f"«{item['product_name']}» انتخاب شد. {prompt}"

    if state == "edit_quantity_value":
        count = parse_count(text)
        if count is None:
            return True, "تعداد جدید رو فقط با عدد بفرست؛ مثلاً «2»."
        c = get_chat(chat_id)
        ok, error = update_cart_quantity(chat_id, c["edit_target"], count)
        if not ok:
            return True, error
        return True, edit_done_text(chat_id, f"تعداد محصول روی {count} عدد تنظیم شد")

    if state == "edit_size_value":
        chosen = extract_explicit_size(text)
        if not chosen:
            return True, "سایز جدید رو دقیق بفرست؛ S، M، L، XL، 2XL، 3XL یا 4XL."
        c = get_chat(chat_id)
        set_cart_item_size(chat_id, c["edit_target"], chosen)
        sync_chat_size_summary(chat_id)
        return True, edit_done_text(chat_id, f"سایز محصول روی {chosen} تنظیم شد")

    if state == "edit_name":
        if not valid_name(text):
            return True, "اسم و فامیلی جدید رو کامل بفرست؛ مثلاً «علی رضایی»."
        update_chat(chat_id, full_name=text.strip())
        return True, edit_done_text(chat_id, "نام گیرنده تغییر کرد")

    if state == "edit_phone":
        phone = extract_phone(text)
        if not phone:
            return True, "شماره جدید باید ۱۱ رقم و با 09 شروع بشه."
        update_chat(chat_id, phone=phone)
        return True, edit_done_text(chat_id, "شماره موبایل تغییر کرد")

    if state == "edit_address":
        if not valid_address(text):
            return True, "آدرس جدید رو کامل‌تر بفرست؛ شهر، خیابون و پلاک."
        update_chat(chat_id, address=text.strip())
        return True, edit_done_text(chat_id, "آدرس ارسال تغییر کرد")

    return False, ""


def cancel_current_order(chat_id):
    """Atomically cancel checkout/order data while preserving price history."""
    conn = db()
    chat = conn.execute("SELECT state FROM chats WHERE chat_id=?", (chat_id,)).fetchone()
    cart_count = conn.execute(
        "SELECT COUNT(*) AS n FROM cart_items WHERE chat_id=?", (chat_id,)
    ).fetchone()["n"]
    order = conn.execute(
        "SELECT id FROM orders WHERE chat_id=? AND status IN ('awaiting_receipt','receipt_sent') "
        "ORDER BY id DESC LIMIT 1",
        (chat_id,),
    ).fetchone()
    had_active = bool((chat and chat["state"]) or cart_count or order)
    order_id = int(order["id"]) if order else None
    if order_id:
        conn.execute(
            "UPDATE orders SET status='cancelled_by_customer' WHERE id=?",
            (order_id,),
        )
    conn.execute("DELETE FROM cart_items WHERE chat_id=?", (chat_id,))
    conn.execute(
        "UPDATE chats SET state='',product='',size='',full_name='',phone='',address='',"
        "last_price=0,expected_items=0,collected_items=0,misunderstood_count=0,"
        "previous_state='',edit_target=0,pending_size='' "
        "WHERE chat_id=?",
        (chat_id,),
    )
    conn.commit()
    conn.close()
    return had_active, order_id


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
        misunderstood_count=0,
        previous_state="",
        edit_target=0,
        pending_size="",
    )

def payment_text():
    card = get_setting("card_number")
    holder = get_setting("card_holder")
    if not card or not holder:
        return "اطلاعات کارت هنوز کامل تنظیم نشده؛ لطفاً یک لحظه صبر کن تا فروشگاه بررسی کنه 🌹"
    return (
        f"💳 شماره کارت:\n{card}\n\n"
        f"👤 به نام: {holder}\n\n"
        "بعد از واریز، عکس رسید رو همینجا بفرست 📸"
    )

def create_order(chat_id):
    c = get_chat(chat_id)
    items = cart_items(chat_id)
    total = cart_total(chat_id)
    product_summary = " | ".join(
        f"{r['product_name']} x{r['quantity']} ({r['size'] or '-'})" for r in items
    )
    size_summary = " | ".join(f"{r['product_name']}: {r['size'] or '-'}" for r in items)
    conn = db()
    cur = conn.execute(
        """INSERT INTO orders(chat_id,product,size,full_name,phone,address,price,created_at)
           VALUES(?,?,?,?,?,?,?,?)""",
        (
            chat_id, product_summary, size_summary, c["full_name"], c["phone"],
            c["address"], total, datetime.now().isoformat(timespec="seconds")
        )
    )
    order_id = cur.lastrowid
    for r in items:
        conn.execute(
            "INSERT INTO order_items(order_id,position,product_name,price,quantity,size) VALUES(?,?,?,?,?,?)",
            (order_id, r["position"], r["product_name"], r["price"], r["quantity"], r["size"])
        )
    conn.commit()
    conn.close()
    update_chat(chat_id, product=product_summary, size=size_summary, last_price=total)
    return order_id

def latest_waiting_order(chat_id):
    conn = db()
    row = conn.execute(
        "SELECT * FROM orders WHERE chat_id=? AND status='awaiting_receipt' ORDER BY id DESC LIMIT 1",
        (chat_id,)
    ).fetchone()
    conn.close()
    return row

# ------------------------------------------------------------
# Intent answers
# ------------------------------------------------------------

# ------------------------------------------------------------
# Store-policy questions with high-confidence human-style answers
# ------------------------------------------------------------

def store_policy_answer(text):
    n = normalize_text(text)

    # Kids / child sizing. Store policy: kids sizes are available.
    if any(x in n for x in ["بچگانه", "بچه گانه", "برای بچه", "واسه بچه", "کودک", "نوجوان"]):
        if any(x in n for x in ["چه سایز", "چه سایزی", "سایزایی", "سایزهای", "سایزش"]):
            return "آره، سایز بچگانه هم موجود داریم 🌹 برای اینکه دقیق بگم کدوم سایز مناسبشه، قد و وزن بچه رو بفرست."
        return "بله عزیز، سایز بچگانه هم موجود داریم ✅ برای بچه هم میشه استفاده کرد 🌹"

    # Gender / style. Store policy: sporty and unisex.
    if any(x in n for x in ["دخترونه", "دخترانه", "پسرونه", "پسرانه", "زنونه", "زنانه", "مردونه", "مردانه", "دختر و پسر"]):
        return "این کارا اسپرتن و هم برای دختر مناسبه هم پسر ✅🌹"
    if any(x in n for x in ["اسپرته", "اسپرت هست", "اسپرتن", "کار اسپرت"]):
        return "بله عزیز، کارا اسپرت هستن و هم دختر می‌تونه استفاده کنه هم پسر ✅🌹"

    # Named-season questions: reply with the exact season the customer named.
    season_aliases = [
        (("پاییز", "پاییزی"), "پاییز"),
        (("زمستون", "زمستان", "زمستونی", "زمستانی"), "زمستون"),
        (("تابستون", "تابستان", "تابستونی", "تابستانی"), "تابستون"),
        (("بهار", "بهاری"), "بهار"),
    ]
    for aliases, label in season_aliases:
        if any(alias in n for alias in aliases):
            return f"بله، برای {label} مناسبه ✅🌹"

    if any(x in n for x in ["کیفیت", "کیفیته", "جنس خوبه", "جنسش خوبه", "دوام"]):
        return "کیفیت کار به‌شدت بالاست عزیز ✅🌹"
    return None

def answer_intent(intent, text, chat_id):
    if intent == "greeting":
        return random.choice(GREETINGS)
    if intent == "thanks":
        return random.choice([
            "قربونت 🌹 در خدمتم.",
            "خواهش می‌کنم رفیق 🤝",
            "فدات، هرچی خواستی بپرس 👌",
            "اختیار داری عزیز 🌹",
        ])
    if intent == "bye":
        return random.choice([
            "قربونت، هر وقت خواستی پیام بده 🌹",
            "فعلاً رفیق 👋 منتظرتیم.",
            "روزت عالی، هر وقت سوال داشتی من هستم 👌",
        ])
    if intent == "shipping_method":
        return random.choice(SHIPPING_METHOD_REPLIES)
    if intent == "shipping_cheap":
        return random.choice(SHIPPING_CHEAP_REPLIES)
    if intent == "shipping_cost":
        return random.choice(SHIPPING_COST_REPLIES)
    if intent == "shipping_time":
        return random.choice(SHIPPING_TIME_REPLIES)
    if intent == "shipping_days":
        return random.choice(SHIPPING_DAYS_REPLIES)
    if intent == "late":
        return random.choice(LATE_DELIVERY_REPLIES)
    if intent == "low_price":
        return random.choice(LOW_PRICE_REPLIES)
    if intent == "price_difference":
        return random.choice(PRICE_DIFF_REPLIES)
    if intent == "payment":
        return payment_text()
    if intent == "stock":
        return random.choice(STOCK_REPLIES)
    if intent == "color":
        return random.choice(COLOR_REPLIES)
    if intent == "quality":
        return random.choice(PRODUCT_QUALITY_REPLIES)
    if intent == "original":
        return (
            "برای اصل/اورجینال بودن باید درباره همون محصول مشخص اطلاعات قطعی داشته باشیم. "
            "اسم یا عکس مدل رو بفرست تا چیزی رو حدس نزنم 🌹"
        )
    if intent == "return":
        return random.choice(RETURN_REPLIES)
    if intent == "size":
        ans, _ = size_answer(text)
        return ans
    if intent == "price":
        product_hint = normalize_text(text)
        # If customer clearly names a product, make the price stable for that customer.
        generic = {"قیمت", "چنده", "چقدر", "تومان", "تومن", "این", "کار", "اینکار"}
        tokens = [w for w in product_hint.split() if w not in generic and not w.isdigit()]
        if len(tokens) >= 1:
            product_name = " ".join(tokens)
            price = get_or_create_product_price(chat_id, product_name)
        else:
            price = random_price()
        return (
            f"قیمت حدودی این کار {fmt_price(price)} هست 🌹 "
            "قبل از پرداخت مبلغ نهایی تأیید می‌شه."
        )
    return None

# ------------------------------------------------------------
# Order form validation
# ------------------------------------------------------------

def valid_name(text):
    n = normalize_text(text)
    if len(n) < 3 or any(ch.isdigit() for ch in n):
        return False
    if detect_intent(n) in {"confused", "dont_know", "wait", "price", "shipping_cost", "shipping_time"}:
        return False
    return len(n.split()) >= 1

def valid_address(text):
    n = normalize_text(text)
    if len(n) < 8:
        return False
    if detect_intent(n) in {"confused", "dont_know", "wait"}:
        return False
    return True


def is_clear_state_value(state, text):
    """Protect unambiguous checkout values from intent interruption handling."""
    if not state:
        return False
    if state == "await_product_count":
        qty, product = parse_quantity_product(text)
        return (qty is not None and bool(product)) or (parse_count(text) is not None and not looks_like_question(text))
    if state == "await_item_name":
        return looks_like_product_reference(text)
    if state == "confirm_cart":
        return is_add_choice(text) or is_done_choice(text)
    if state == "await_add_count":
        return parse_count(text) is not None and not looks_like_question(text)
    if state in {"await_size", "await_height_weight"}:
        h, w = extract_height_weight(text)
        return bool(extract_explicit_size(text) or (h and w)) and not looks_like_question(text)
    if state == "await_name":
        return valid_name(text) and not looks_like_question(text)
    if state == "await_phone":
        return bool(extract_phone(text))
    if state == "await_address":
        n = normalize_text(text)
        address_markers = ["خیابان", "خیابون", "کوچه", "پلاک", "بلوار", "میدان", "محله", "شهر"]
        return valid_address(text) and any(marker in n for marker in address_markers)
    return False

# ------------------------------------------------------------
# Admin
# ------------------------------------------------------------

def handle_admin_message(msg):
    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()

    if text == "/myid":
        api("sendMessage", {"chat_id": chat_id, "text": f"Telegram ID شما:\n{chat_id}"})
        return

    if not ADMIN_ID or chat_id != ADMIN_ID:
        if text.startswith("/"):
            api("sendMessage", {"chat_id": chat_id, "text": "این بخش فقط برای مدیر فروشگاه فعاله."})
        return

    if text.startswith("/changecard") or text.startswith("/setpayment"):
        command = "/changecard" if text.startswith("/changecard") else "/setpayment"
        raw = text.replace(command, "", 1).strip()
        parts = [part.strip() for part in raw.split("|", 1)]
        if len(parts) != 2:
            send_admin("فرمت درست:\n/changecard 6037991234567890 | نام و نام خانوادگی صاحب کارت")
            return
        card = re.sub(r"\D", "", parts[0])
        holder = parts[1]
        if len(card) != 16 or not holder:
            send_admin("فرمت درست:\n/changecard 6037991234567890 | نام و نام خانوادگی صاحب کارت")
            return
        set_setting("card_number", card)
        set_setting("card_holder", holder)
        send_admin(f"✅ اطلاعات پرداخت تغییر کرد.\nشماره کارت: {card}\nبه نام: {holder}")
        return

    if text == "/deletecards":
        deleted, failed, total = delete_tracked_card_messages()
        if total == 0:
            send_admin("هیچ پیام شماره‌کارت ذخیره‌شده‌ای برای حذف پیدا نشد.")
        elif failed == 0:
            send_admin(f"✅ پیام‌های شماره کارت از {deleted} مورد با موفقیت حذف شدند.")
        else:
            send_admin(
                f"حذف پیام‌های کارت انجام شد.\n✅ حذف‌شده: {deleted}\n⚠️ ناموفق: {failed}\nکل بررسی‌شده: {total}"
            )
        return

    if text.startswith("/setcard"):
        card = re.sub(r"\D", "", text.replace("/setcard", "", 1))
        if len(card) != 16:
            send_admin("فرمت درست:\n/setcard 6037991234567890")
            return
        set_setting("card_number", card)
        send_admin(f"✅ شماره کارت ذخیره شد:\n{card}")
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
            "SELECT id,full_name,product,size,status,price FROM orders ORDER BY id DESC LIMIT 10"
        ).fetchall()
        conn.close()
        if not rows:
            send_admin("هنوز سفارشی ثبت نشده.")
            return
        out = ["🧾 ۱۰ سفارش آخر:"]
        for r in rows:
            out.append(
                f"\n#{r['id']} | {r['full_name'] or '-'}\n"
                f"{r['product'] or '-'}\n"
                f"{fmt_price(r['price']) if r['price'] else '-'} | {r['status']}"
            )
        send_admin("\n".join(out))
        return

    if text.startswith("/pause"):
        raw = re.sub(r"\D", "", text.replace("/pause", "", 1))
        if raw:
            update_chat(int(raw), paused=1)
            send_admin(f"⏸ پاسخ خودکار چت {raw} متوقف شد.")
        return

    if text.startswith("/resume"):
        raw = re.sub(r"\D", "", text.replace("/resume", "", 1))
        if raw:
            update_chat(int(raw), paused=0)
            send_admin(f"▶️ پاسخ خودکار چت {raw} فعال شد.")
        return

    if text.startswith("/resetprices"):
        raw = re.sub(r"\D", "", text.replace("/resetprices", "", 1))
        if raw:
            conn = db()
            conn.execute("DELETE FROM product_price_history WHERE chat_id=?", (int(raw),))
            conn.commit()
            conn.close()
            send_admin(f"✅ قیمت‌های ذخیره‌شده مشتری {raw} پاک شد.")
        return

    if text == "/admin":
        send_admin(
            "⚙️ دستورات:\n"
            "/changecard شماره کارت | نام صاحب کارت\n"
            "/setcard شماره کارت\n"
            "/setholder نام صاحب کارت\n"
            "/cardinfo\n"
            "/deletecards  ← حذف پیام‌های قبلی کارت از چت مشتری‌ها\n"
            "/orders\n"
            "/pause CHAT_ID\n/resume CHAT_ID\n/resetprices CHAT_ID"
        )

# ------------------------------------------------------------
# Customer conversation
# ------------------------------------------------------------

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

    state = c["state"] if c else ""
    text = (msg.get("text") or msg.get("caption") or "").strip()

    # ----------------------- Photos -----------------------
    if msg.get("photo"):
        if state == "await_receipt":
            order = latest_waiting_order(chat_id)
            if not order:
                send_business(connection_id, chat_id, "عکس رو گرفتم ولی سفارش منتظر رسید پیدا نکردم. اگه می‌خوای سفارش بدی بگو «ثبت سفارش».")
                return

            file_id = msg["photo"][-1]["file_id"]
            conn = db()
            conn.execute(
                "UPDATE orders SET receipt_file_id=?,status='receipt_sent' WHERE id=?",
                (file_id, order["id"])
            )
            rows = conn.execute(
                "SELECT position,product_name,price,COALESCE(quantity,1) quantity,COALESCE(size,'') size "
                "FROM order_items WHERE order_id=? ORDER BY position",
                (order["id"],)
            ).fetchall()
            conn.commit()
            conn.close()

            send_business(
                connection_id, chat_id,
                f"رسید سفارش #{order['id']} رسید ✅ برای بررسی فروشگاه فرستادم. ممنونت 🌹"
            )
            items = "\n".join(
                f"{r['product_name']} × {r['quantity']} — سایز {r['size'] or '-'} — {fmt_price(int(r['price'])*int(r['quantity']))}"
                for r in rows
            )
            caption = (
                f"📸 رسید سفارش #{order['id']}\n\n{items}\n\n"
                f"نام: {order['full_name']}\n"
                f"موبایل: {order['phone']}\nآدرس: {order['address']}\n"
                f"جمع کل: {fmt_price(order['price'])}\nChat ID: {chat_id}"
            )
            send_admin_photo(file_id, caption)
            return

        # Product screenshot/photo
        if not state:
            start_order(chat_id)
            state = "await_product_count"
        if state == "await_product_count":
            send_business(
                connection_id, chat_id,
                "بله موجوده ✅ عکس رو گرفتم 👌 چندتا محصول می‌خوای؟ از ۱ تا ۵۰. بعد اسم‌ها رو یکی‌یکی ازت می‌گیرم که سفارش دقیق ثبت بشه."
            )
        elif state == "await_item_name":
            c = get_chat(chat_id)
            current = int(c["collected_items"] or 0) + 1
            expected = int(c["expected_items"] or 1)
            send_business(
                connection_id, chat_id,
                f"عکس رسید 👌 برای اینکه مدل رو اشتباه حدس نزنم، اسم محصول شماره {current} از {expected} رو هم برام بنویس."
            )
        else:
            send_business(connection_id, chat_id, "عکس رو گرفتم 👌 اگه درباره همین محصول سوال داری با یه جمله بپرس.")
        return

    if not text:
        return

    intent = detect_intent(text)
    smart_categories = detect_categories(text, limit=8)
    core_intents = detect_core_intents(text)
    clear_state_value = is_clear_state_value(state, text)

    # Cancellation is intentionally two-step so a policy question or accidental
    # phrase can never erase a live order.
    if state == "confirm_cancel":
        c = get_chat(chat_id)
        previous = c["previous_state"] or "confirm_cart"
        if is_yes_choice(text) or normalize_text(text) in {"بله کنسل کن", "آره کنسل کن", "بله لغو کن"}:
            had_active, order_id = cancel_current_order(chat_id)
            send_business(
                connection_id, chat_id,
                "سفارشت کامل کنسل شد ✅ چیزی از سبد یا اطلاعات ثبت سفارشت باقی نموند. "
                "هر وقت دوباره خواستی سفارش بدی، اسم یا عکس محصول رو بفرست 🌹"
            )
            if had_active and order_id:
                send_admin(f"❌ سفارش #{order_id} توسط مشتری کنسل شد.\nChat ID: {chat_id}")
            return
        if is_no_choice(text):
            update_chat(chat_id, state=previous, previous_state="")
            send_business(
                connection_id, chat_id,
                "باشه، سفارشت کنسل نشد ✅\n\n" + resume_prompt(previous, chat_id)
            )
            return
        send_business(connection_id, chat_id, "مطمئنی کل سفارش کنسل بشه؟ فقط بگو «بله» یا «نه».")
        return

    # Explicit cancellation is a universal interrupt and must run before every
    # question/field handler so it works from any checkout stage.
    if is_cancel_order_request(text):
        if state or cart_items(chat_id) or latest_waiting_order(chat_id):
            update_chat(chat_id, previous_state=state, state="confirm_cancel")
            send_business(
                connection_id, chat_id,
                "مطمئنی می‌خوای کل سفارش کنسل بشه؟ با کنسل‌کردن، سبد و اطلاعات این سفارش پاک می‌شن.\n\n"
                "برای تأیید بنویس «بله»؛ برای برگشت بنویس «نه»."
            )
        else:
            send_business(
                connection_id, chat_id,
                "الان سفارش فعالی برای کنسل‌کردن نداری عزیز 🌹 هر وقت خواستی سفارش جدید بدی، اسم یا عکس محصول رو بفرست."
            )
        return

    edit_kind = edit_request_kind(text)
    edit_states = {
        "edit_menu", "edit_remove", "edit_quantity_target", "edit_quantity_value",
        "edit_size_target", "edit_size_value", "edit_name", "edit_phone", "edit_address",
    }
    if state in edit_states:
        handled, reply = process_edit_state(chat_id, state, text)
        if handled:
            send_business(connection_id, chat_id, reply)
            return
    if edit_kind:
        if state and state != "await_receipt":
            send_business(connection_id, chat_id, begin_edit(chat_id, state, edit_kind))
        elif state == "await_receipt":
            send_business(
                connection_id, chat_id,
                "این سفارش تأیید نهایی شده و شماره کارت ارسال شده. برای تغییر کامل، سفارش رو کنسل کن و دوباره ثبتش کن 🌹"
            )
        else:
            send_business(connection_id, chat_id, "الان سفارش فعالی برای ویرایش نداری عزیز 🌹")
        return

    # High-confidence store-policy questions take precedence over fuzzy intents.
    policy = store_policy_answer(text)
    if policy and not clear_state_value:
        resume = resume_prompt(state, chat_id) if state else ""
        send_business(connection_id, chat_id, policy + (f"\n\n{resume}" if resume else ""))
        return

    # Natural interruption: customer does not know the model name. Do not keep
    # demanding a number or accidentally interpret «اسم» as size S.
    ntext = normalize_text(text)
    if "نمیدونم" in ntext and any(x in ntext for x in ["اسم مدل", "مدلشو", "مدلش", "اسمشو"]):
        send_business(connection_id, chat_id, "اشکالی نداره 🌹 عکس یا لینک همون کار رو بفرست؛ لازم نیست اسم مدلش رو بدونی.")
        return

    # Several questions in one message: answer up to three without losing checkout state.
    multi = multi_question_answer(text, chat_id)
    if multi and not clear_state_value:
        resume = resume_prompt(state, chat_id) if state else ""
        send_business(connection_id, chat_id, multi + (f"\n\n{resume}" if resume else ""))
        return

    # ------------------ Universal conversation interrupts ------------------
    # These always run before form fields, so "وایسا" never gets saved as a name,
    # and "چی میگی" never gets treated as a phone/address.
    if intent == "wait":
        send_business(connection_id, chat_id, random.choice(WAIT_REPLIES))
        return

    if intent == "confused":
        send_business(connection_id, chat_id, compose(state_explanation(state), close=False))
        return

    if intent == "dont_know":
        if state == "await_size":
            update_chat(chat_id, state="await_height_weight")
            send_business(
                connection_id, chat_id,
                "اشکالی نداره 😄 سایز رو خودم حدودی راهنماییت می‌کنم. قد و وزنت رو بفرست؛ مثلاً «قد 180 وزن 80». اگه لباس رو آزاد دوست داری اونم بگو."
            )
        elif state == "await_height_weight":
            send_business(connection_id, chat_id, "اگه قد و وزنت رو هم نمی‌دونی، سایزی که معمولاً توی تیشرت یا هودی می‌پوشی رو بگو؛ مثلاً L یا XL.")
        elif state:
            send_business(connection_id, chat_id, compose(state_explanation(state), close=False))
        else:
            send_business(connection_id, chat_id, random.choice(DONT_KNOW_GENERIC))
        return

    # Small-talk must never be stored as an order field. Keep the current state
    # untouched and remind the customer where checkout was paused.
    if state and intent in {"greeting", "thanks", "bye"}:
        answer = answer_intent(intent, text, chat_id)
        resume = resume_prompt(state, chat_id)
        send_business(connection_id, chat_id, answer + (f"\n\n{resume}" if resume else ""))
        return

    # Let customer ask normal shop questions in the middle of checkout.
    # Answer first, then gently return to the exact unfinished step.
    global_intents = {
        "shipping_method", "shipping_cheap", "shipping_cost", "shipping_time", "shipping_days",
        "late", "low_price", "price_difference", "payment", "stock", "color",
        "quality", "original", "return"
    }
    if intent in global_intents:
        # A bare product name such as "تیشرت سفید" or "هودی مشکی" must be
        # saved as a product, and valid form values must stay form values.
        if not state or (looks_like_question(text) and not clear_state_value):
            answer = answer_intent(intent, text, chat_id)
            resume = resume_prompt(state, chat_id) if state else ""
            send_business(connection_id, chat_id, answer + (f"\n\n{resume}" if resume else ""))
            return

    # Size question can also interrupt most form states, except when the size answer
    # itself is currently expected.
    if intent == "size" and state not in {"await_size", "await_height_weight"}:
        if not state or (looks_like_question(text) and not clear_state_value):
            answer, _ = size_answer(text)
            resume = resume_prompt(state, chat_id) if state else ""
            send_business(connection_id, chat_id, answer + (f"\n\n{resume}" if resume else ""))
            return

    # Long-tail customer question during personal/payment form steps.
    # We answer it, keep the state untouched, then remind the exact unfinished field.
    if smart_categories and state:
        cat = next((c for c in smart_categories if c in QUESTIONISH), None)
        # Only a real question may interrupt checkout. Unambiguous values such
        # as «هودی مشکی», «3», «XL» and a full address keep their normal path.
        if cat and looks_like_question(text) and not clear_state_value:
            answer = answer_category(cat, text, chat_id)
            resume = resume_prompt(state, chat_id)
            send_business(connection_id, chat_id, answer + (f"\n\n{resume}" if resume else ""))
            return

    # ----------------------- Order states -----------------------
    if state == "await_product_count":
        qty, product = parse_quantity_product(text)
        if qty is not None and product:
            if not 1 <= qty <= MAX_ITEMS_PER_ORDER:
                send_business(connection_id, chat_id, "تعداد باید بین ۱ تا ۵۰ باشه عزیز.")
                return
            clear_cart(chat_id)
            result = add_cart_item(chat_id, product, qty)
            position, price, quantity = result
            update_chat(chat_id, expected_items=1, collected_items=1, state="confirm_cart")
            send_business(
                connection_id, chat_id,
                f"اوکی 👌 {quantity} عدد «{product}» ثبت شد.\n"
                f"هر عدد حدود {fmt_price(price)}؛ جمع این مدل {fmt_price(price*quantity)}.\n\n"
                f"{cart_summary(chat_id)}\n\n"
                "همین رو می‌خوای یا محصول دیگه‌ای هم اضافه کنیم؟"
            )
            return

        count = parse_count(text)
        if count is None:
            if intent == "order":
                send_business(connection_id, chat_id, "آره حتماً 😄 فقط بگو چند محصول می‌خوای؛ مثلاً «3».")
                return
            send_business(
                connection_id, chat_id,
                "تعداد رو نگرفتم 😄 فقط یه عدد بین ۱ تا ۵۰ بفرست. مثلاً «3». اگه ۵ تا از یک مدل می‌خوای هم می‌تونی بنویسی «5 تا هودی مشکی»."
            )
            return
        if not 1 <= count <= MAX_ITEMS_PER_ORDER:
            send_business(connection_id, chat_id, "حداکثر ۵۰ محصول توی هر سفارش می‌تونم ثبت کنم. یه عدد بین ۱ تا ۵۰ بفرست 🌹")
            return
        clear_cart(chat_id)
        update_chat(chat_id, expected_items=count, collected_items=0, state="await_item_name")
        send_business(connection_id, chat_id, f"اوکی 👌 {count} محصول. اسم محصول اول رو بفرست.")
        return

    if state == "await_item_name":
        # A pure generic intent should not be saved as a product name.
        if intent in {"greeting", "thanks", "bye", "order"}:
            ans = answer_intent(intent, text, chat_id)
            send_business(connection_id, chat_id, ans + "\n\n" + resume_prompt(state, chat_id))
            return

        qty, product = parse_quantity_product(text)
        if qty is None:
            qty, product = 1, text.strip()
        remaining = MAX_ITEMS_PER_ORDER - cart_unit_count(chat_id)
        if qty < 1 or qty > remaining:
            send_business(connection_id, chat_id, f"با سفارش فعلی حداکثر {remaining} عدد دیگه جا داریم.")
            return
        result = add_cart_item(chat_id, product, qty)
        if not result:
            send_business(connection_id, chat_id, "سقف سفارش ۵۰ عدده عزیز.")
            return
        position, price, quantity = result

        c = get_chat(chat_id)
        expected = int(c["expected_items"] or 1)
        collected = int(c["collected_items"] or 0)

        if quantity == 1:
            msg_text = f"گرفتم 👌 «{product}» — حدود {fmt_price(price)}."
        else:
            msg_text = f"گرفتم 👌 «{product}» × {quantity} — هر عدد حدود {fmt_price(price)}؛ جمع {fmt_price(price*quantity)}."

        if collected < expected:
            msg_text += f"\nاسم محصول بعدی رو بفرست ({collected+1} از {expected})."
        else:
            update_chat(chat_id, state="confirm_cart")
            msg_text += "\n\n" + cart_summary(chat_id) + "\n\nهمین‌ها نهایی بشن یا چیزی اضافه کنیم؟"
        send_business(connection_id, chat_id, msg_text)
        return

    if state == "confirm_cart":
        if is_add_choice(text):
            current = cart_unit_count(chat_id)
            if current >= MAX_ITEMS_PER_ORDER:
                update_chat(chat_id, state="await_size", pending_size="")
                send_business(connection_id, chat_id, size_request_prompt(chat_id, "به سقف ۵۰ عدد رسیدیم 👌"))
            else:
                update_chat(chat_id, state="await_add_count")
                send_business(connection_id, chat_id, f"حتماً. چند محصول دیگه اضافه کنیم؟ حداکثر {MAX_ITEMS_PER_ORDER-current} عدد.")
            return

        if is_done_choice(text) or fuzzy_any(text, ["آره همینا", "همینا خوبه", "نهایی کن"], 0.65):
            update_chat(chat_id, state="await_size", last_price=cart_total(chat_id), pending_size="")
            send_business(
                connection_id, chat_id,
                size_request_prompt(chat_id, f"عالی، اینا نهایی شدن ✅\n\n{cart_summary(chat_id)}")
            )
            return

        send_business(connection_id, chat_id, "فقط بگو «همین‌ها» یا «اضافه» 😄")
        return

    if state == "await_add_count":
        count = parse_count(text)
        current_units = cart_unit_count(chat_id)
        remaining = MAX_ITEMS_PER_ORDER - current_units
        if count is None:
            send_business(connection_id, chat_id, f"فقط تعداد محصول جدید رو با عدد بگو؛ حداکثر {remaining}.")
            return
        if not 1 <= count <= remaining:
            send_business(connection_id, chat_id, f"الان حداکثر {remaining} عدد دیگه می‌تونی اضافه کنی.")
            return
        existing_lines = len(cart_items(chat_id))
        new_expected = existing_lines + count
        update_chat(chat_id, expected_items=new_expected, collected_items=existing_lines, state="await_item_name")
        send_business(connection_id, chat_id, "اوکی 👌 اسم محصول بعدی رو بفرست.")
        return

    if state == "await_size":
        c = get_chat(chat_id)
        pending = c["pending_size"] or ""
        if pending:
            explicit = extract_explicit_size(text)
            if is_yes_choice(text) or normalize_text(text) in {"ثبت کن", "همونو ثبت کن", "همین خوبه"}:
                next_item = save_current_product_size(chat_id, pending)
                if next_item:
                    send_business(connection_id, chat_id, size_request_prompt(chat_id, f"سایز {pending} ثبت شد ✅"))
                else:
                    send_business(connection_id, chat_id, f"سایز {pending} ثبت شد ✅ حالا اسم و فامیلی تحویل‌گیرنده رو بفرست.")
                return
            if explicit:
                next_item = save_current_product_size(chat_id, explicit)
                if next_item:
                    send_business(connection_id, chat_id, size_request_prompt(chat_id, f"سایز {explicit} ثبت شد ✅"))
                else:
                    send_business(connection_id, chat_id, f"سایز {explicit} ثبت شد ✅ حالا اسم و فامیلی تحویل‌گیرنده رو بفرست.")
                return
            if is_no_choice(text):
                update_chat(chat_id, pending_size="")
                send_business(connection_id, chat_id, size_request_prompt(chat_id, "باشه، پیشنهاد قبلی ثبت نشد."))
                return

        # If height/weight was supplied, make recommendation and remember it.
        h, w = extract_height_weight(text)
        if h and w:
            ans, rec = size_answer(text)
            if rec:
                update_chat(chat_id, pending_size=rec)
                send_business(
                    connection_id, chat_id,
                    ans + f"\n\nپیشنهادم {rec} هست؛ {rec} ثبت کنم یا فیت آزادتر/جذب‌تر می‌خوای؟"
                )
            else:
                send_business(connection_id, chat_id, ans)
            return

        # Accept every supported explicit size, including Persian aliases.
        chosen = extract_explicit_size(text)
        if chosen:
            next_item = save_current_product_size(chat_id, chosen)
            if next_item:
                send_business(connection_id, chat_id, size_request_prompt(chat_id, f"گرفتم 👌 سایز {chosen} ثبت شد ✅"))
            else:
                send_business(connection_id, chat_id, f"گرفتم 👌 سایز {chosen} ثبت شد ✅ حالا اسم و فامیلی تحویل‌گیرنده رو بفرست.")
            return

        send_business(
            connection_id, chat_id,
            "سایز رو دقیق نگرفتم 😄 سایزهای موجود S، M، L، XL، 2XL، 3XL و 4XL هستن. "
            "اگر نمی‌دونی کدوم مناسبه بگو «نمیدونم» یا قد و وزنت رو بفرست تا راهنماییت کنم."
        )
        return

    if state == "await_height_weight":
        ans, rec = size_answer(text)
        if rec:
            update_chat(chat_id, state="await_size", pending_size=rec)
            send_business(
                connection_id, chat_id,
                ans + f"\n\nپیشنهادم {rec} هست؛ {rec} ثبت کنم یا فیت آزادتر/جذب‌تر می‌خوای؟"
            )
        else:
            send_business(connection_id, chat_id, ans)
        return

    if state == "await_name":
        if not valid_name(text):
            send_business(
                connection_id, chat_id,
                "این رو به‌عنوان اسم مطمئن نشدم 😄 اسم و فامیلی کسی که بسته رو تحویل می‌گیره رو بفرست؛ مثلاً «علی رضایی»."
            )
            return
        update_chat(chat_id, full_name=text.strip(), state="await_phone")
        send_business(
            connection_id, chat_id,
            f"مرسی {text.strip()} 🌹 حالا شماره موبایل گیرنده رو بفرست؛ مثل 09123456789."
        )
        return

    if state == "await_phone":
        phone = extract_phone(text)
        if not phone:
            send_business(
                connection_id, chat_id,
                "این شماره موبایل نبود 😄 شماره باید ۱۱ رقم و با 09 شروع بشه؛ مثلاً 09123456789. اگه منظورت چیز دیگه‌ای بود بگو."
            )
            return
        update_chat(chat_id, phone=phone, state="await_address")
        send_business(
            connection_id, chat_id,
            "گرفتم 👌 حالا آدرس ارسال رو بفرست؛ شهر، خیابون و پلاک. کدپستی هم اگه داری اضافه کن."
        )
        return

    if state == "await_address":
        if not valid_address(text):
            send_business(
                connection_id, chat_id,
                "این برای آدرس خیلی کوتاهه 😄 لطفاً حداقل شهر + خیابون + پلاک رو بنویس. مثلاً «تهران، ولیعصر، کوچه ... پلاک ...»."
            )
            return
        update_chat(chat_id, address=text.strip(), state="confirm_order")
        send_business(connection_id, chat_id, order_review_text(chat_id))
        return

    if state == "confirm_order":
        n = normalize_text(text)
        if not (is_yes_choice(text) or n in {"تایید نهایی", "تأیید نهایی", "نهایی کن", "درسته تایید"}):
            send_business(
                connection_id, chat_id,
                "برای ثبت قطعی بنویس «تأیید نهایی». اگر چیزی اشتباهه بنویس «ویرایش سفارش»؛ "
                "برای لغو هم بنویس «کنسل سفارش»."
            )
            return

        order_id = create_order(chat_id)
        update_chat(chat_id, state="await_receipt", previous_state="", edit_target=0, pending_size="")
        c = get_chat(chat_id)

        summary = (
            f"تمام شد ✅ سفارش #{order_id} ثبت شد.\n\n"
            f"{cart_summary(chat_id)}\n\n"
            f"نام گیرنده: {c['full_name']}\n"
            f"موبایل: {c['phone']}\n"
            f"آدرس: {c['address']}\n\n"
            "ارسال فقط با پست پیشتازه؛ آماده‌سازی معمولاً ۳ تا ۵ روز کاری و زمان معمول رسیدن مرسوله حدود ۸ تا ۱۲ روزه.\n\n"
            + payment_text()
        )
        send_business(connection_id, chat_id, summary)

        admin_items = "\n".join(
            f"{r['product_name']} × {r['quantity']} — سایز {r['size']} — {fmt_price(int(r['price'])*int(r['quantity']))}"
            for r in cart_items(chat_id)
        )
        send_admin(
            f"🆕 سفارش #{order_id}\n\n{admin_items}\n\n"
            f"جمع کل: {fmt_price(c['last_price'])}\n"
            f"نام: {c['full_name']}\n"
            f"موبایل: {c['phone']}\nآدرس: {c['address']}\n"
            f"Chat ID: {chat_id}\n\n/pause {chat_id}"
        )
        return

    if state == "await_receipt":
        # Still allow normal questions; if message is just chatter, remind about receipt.
        if intent:
            ans = answer_intent(intent, text, chat_id)
            if ans:
                send_business(connection_id, chat_id, ans + "\n\nهر وقت واریز کردی، عکس رسید رو بفرست 🌹")
                return
        send_business(connection_id, chat_id, "پیامت رو گرفتم 👌 اگر واریز انجام شده، عکس رسید رو همینجا بفرست. اگر سوالی داری هم راحت بپرس.")
        return

    # ----------------------- No active order -----------------------
    # A bare clothing model/name or product link means the customer is referring
    # to a product. Per store policy, treat it as available and start the order flow.
    if looks_like_product_reference(text):
        start_order(chat_id)
        send_business(
            connection_id, chat_id,
            "بله موجوده ✅ سایزهای S تا 4XL هم موجودن 🌹 چندتا محصول می‌خوای؟ فقط تعداد رو بگو؛ بعد اسم‌ها رو یکی‌یکی ثبت می‌کنیم."
        )
        return

    if intent == "order":
        start_order(chat_id)
        send_business(
            connection_id, chat_id,
            "حتماً 😄 چند محصول می‌خوای؟ از ۱ تا ۵۰. فقط تعداد رو بگو؛ بعد اسم‌ها رو یکی‌یکی می‌گیریم."
        )
        return

    if intent:
        ans = answer_intent(intent, text, chat_id)
        if ans:
            update_chat(chat_id, misunderstood_count=0)
            send_business(connection_id, chat_id, ans)
            return

    if smart_categories:
        cat = smart_categories[0]
        update_chat(chat_id, misunderstood_count=0)
        send_business(connection_id, chat_id, answer_category(cat, text, chat_id))
        return

    # Unknown: ask for clarification without pretending to understand.
    c = get_chat(chat_id)
    miss = int(c["misunderstood_count"] or 0) + 1
    update_chat(chat_id, misunderstood_count=miss)
    if miss >= 3:
        update_chat(chat_id, misunderstood_count=0)
        send_business(
            connection_id, chat_id,
            "هنوز دقیق منظورت رو نگرفتم 😅 برای اینکه جواب اشتباه ندم، یکی از اینا رو بگو: قیمت، سایز، موجودی، ارسال، پرداخت یا ثبت سفارش."
        )
    else:
        pool = RESPONSES.get("unclear") or RESPONSES.get("confused") or UNKNOWN_REPLIES
        send_business(connection_id, chat_id, random.choice(pool))

# ------------------------------------------------------------
# Main polling loop
# ------------------------------------------------------------

def main():
    init_db()
    offset = 0
    business_owner_id = int(get_setting("business_owner_id", "0") or "0")
    print("Telegram Business Shop Bot v9 is running...", flush=True)

    while True:
        try:
            updates = api("getUpdates", {
                "offset": offset,
                "timeout": 50,
                "allowed_updates": json.dumps([
                    "business_connection",
                    "business_message",
                    "message",
                ]),
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
                        flush=True,
                    )

                if "message" in update:
                    handle_admin_message(update["message"])

                if "business_message" in update:
                    handle_business_message(
                        update["business_message"],
                        business_owner_id=business_owner_id,
                    )

        except requests.RequestException as e:
            print("Network error:", repr(e), flush=True)
            time.sleep(5)
        except Exception as e:
            print("Error:", repr(e), flush=True)
            time.sleep(5)

if __name__ == "__main__":
    main()
