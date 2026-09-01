
import os, tempfile, importlib.util, sys
os.environ["BOT_TOKEN"]="TEST_TOKEN"
os.environ["ADMIN_ID"]="1669180525"
os.environ["DB_PATH"]=os.path.join(tempfile.gettempdir(),"shop_v9_test.db")
try: os.remove(os.environ["DB_PATH"])
except FileNotFoundError: pass

sys.path.insert(0, r"/mnt/data/telegram_business_shop_v9_smart")
import main as bot
bot.init_db()

# Never touch Telegram in tests.
sent=[]
bot.send_business=lambda cid,chat,text: sent.append((chat,text))
bot.send_admin=lambda text: None
bot.send_admin_photo=lambda *a,**k: None

cases = {
"قیمط هودی چنذع":"price",
"هزینه پوصت چقده":"shipping_fee",
"تیباکث دارین":"shipping_method",
"سایضم نمیدنم":"size",
"جنسش چیه و آبرفت داره":"fabric",
"کد رهگیریمو میدی":"tracking",
"چرا هنوز نیومده":"late_delivery",
"میشه تعویض سایز کنم":"exchange",
"رنگ بندیش چیه":"color",
"عکس واقعی دارین":"real_photo",
}
print("SMART INTENT TESTS")
ok=0
for msg,want in cases.items():
    cats=bot.detect_categories(msg,limit=5)
    passed=want in cats or bot.CATEGORY_TO_CORE.get(want)==bot.detect_intent(msg)
    ok+=passed
    print(("OK" if passed else "FAIL"), "|", msg, "=>", cats[:3])

# Multi-question
mq="قیمت هودی چنده و هزینه پست چقدره و چند روزه میرسه؟"
print("\nMULTI:", bot.detect_categories(mq,limit=8))
ans=bot.multi_question_answer(mq,12345)
print("multi answer exists:", bool(ans), "parts:", ans.count("• ") if ans else 0)

# Conversation state tests matching the previously broken flow.
chat=555001
bot.ensure_chat(chat,"biz-test")
bot.start_order(chat)
def msg(text):
    sent.clear()
    bot.handle_business_message({
        "business_connection_id":"biz-test",
        "chat":{"id":chat},
        "from":{"id":999},
        "text":text
    }, business_owner_id=111)
    state=bot.get_chat(chat)["state"]
    return state, sent[-1][1] if sent else ""

sequence=[
("3","await_item_name"),
("هودی مشکی","await_item_name"),
("تیشرت سفید","await_item_name"),
("دورس طوسی","confirm_cart"),
("همین‌ها","await_size"),
("بلد نیستم","await_height_weight"),
("چی میگی","await_height_weight"),
("وایسا","await_height_weight"),
("قد 180 وزن 80 آزاد","await_name"),
("چی میگی","await_name"),
("علی رضایی","await_phone"),
("وایسا","await_phone"),
("اه","await_phone"),
("09123456789","await_address"),
("هزینه پوصت چقده","await_address"),
("تهران، ولیعصر، کوچه 10، پلاک 20","await_receipt"),
]
print("\nSTATE MACHINE TESTS")
state_ok=0
for text,want in sequence:
    got,reply=msg(text)
    passed=(got==want)
    state_ok+=passed
    print(("OK" if passed else "FAIL"), "|", text, "=>", got, "|", reply[:85].replace("\n"," "))

# Price stability
p1=bot.get_or_create_product_price(chat,"هودی مشکی")
p2=bot.get_or_create_product_price(chat,"هودی مشکی")
print("\nPRICE STABILITY:", "OK" if p1==p2 else "FAIL", p1,p2)

# 100k bank
total=sum(len(v) for v in bot.RESPONSES.values())
unique=len({x for v in bot.RESPONSES.values() for x in v})
print("BANK:", total, unique)
print(f"\nSUMMARY smart={ok}/{len(cases)} state={state_ok}/{len(sequence)}")
