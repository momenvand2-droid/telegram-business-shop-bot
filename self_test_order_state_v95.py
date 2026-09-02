import os
import tempfile

os.environ["BOT_TOKEN"] = "TEST_TOKEN"
os.environ["ADMIN_ID"] = "0"
os.environ["DB_PATH"] = os.path.join(tempfile.gettempdir(), "shop_v95_state_test.db")
try:
    os.remove(os.environ["DB_PATH"])
except FileNotFoundError:
    pass

import main as bot

bot.init_db()
sent = []
bot.send_business = lambda connection_id, chat_id, text: sent.append(text)
admin_sent = []
bot.send_admin = lambda text: admin_sent.append(text)

# Admin can configure and inspect the wholesale-order username from Telegram.
bot.ADMIN_ID = 70001
bot.handle_admin_message({"chat": {"id": 70001}, "text": "/setwholesale @omde_admin"})
assert bot.get_setting("wholesale_admin_username") == "@omde_admin"
bot.handle_admin_message({"chat": {"id": 70001}, "text": "/wholesaleinfo"})
assert "@omde_admin" in admin_sent[-1]

chat = 95001
bot.ensure_chat(chat, "biz")
bot.add_cart_item(chat, "هودی")
bot.add_cart_item(chat, "تیشرت")
bot.update_chat(chat, state="await_size")

def say(text):
    bot.handle_business_message(
        {"business_connection_id": "biz", "chat": {"id": chat}, "from": {"id": 999}, "text": text},
        business_owner_id=111,
    )

say("2X")
assert bot.cart_items(chat)[0]["size"] == "2XL"
assert bot.get_chat(chat)["state"] == "await_size"

say("قدم 187 وزنم 60")
assert bot.get_chat(chat)["state"] == "confirm_size"
assert bot.get_chat(chat)["pending_size"] == "L"
say("همون ام خوبه")
assert [r["size"] for r in bot.cart_items(chat)] == ["2XL", "L"]
assert bot.get_chat(chat)["state"] == "await_name"

# Material questions use the product description, and wholesale requests are
# redirected without being saved as retail order data or changing the state.
say("جنس محصول چیه؟")
assert bot.get_chat(chat)["state"] == "await_name"
assert "توضیحات" in sent[-1] and "فقط مسئول ثبت سفارش" in sent[-1]
item_count = len(bot.cart_items(chat))
say("سفارش عمده میخوام")
assert bot.get_chat(chat)["state"] == "await_name"
assert len(bot.cart_items(chat)) == item_count
assert "@omde_admin" in sent[-1]

say("رضا رضا")
assert bot.get_chat(chat)["state"] == "await_phone"
say("نمیخوام")
assert bot.get_chat(chat)["state"] == "confirm_cancel"
say("نه ادامه بده")
assert bot.get_chat(chat)["state"] == "await_phone"

say("09123456789")
assert bot.get_chat(chat)["state"] == "await_address"
say("تهران خوبه")
assert bot.get_chat(chat)["state"] == "await_address"
say("تهران خیابان هندی کوچه مقامی پلاک 12")
assert bot.get_chat(chat)["state"] == "confirm_order"

conn = bot.db()
assert conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
conn.close()
assert "شماره کارت" in sent[-1] and "بعد از تأیید" in sent[-1]

say("هزینه پست چنده")
assert bot.get_chat(chat)["state"] == "confirm_order"
say("ویرایش")
assert bot.get_chat(chat)["state"] == "edit_menu"
say("موبایل")
assert bot.get_chat(chat)["state"] == "edit_phone"
say("09991234567")
assert bot.get_chat(chat)["state"] == "confirm_order"
assert bot.get_chat(chat)["phone"] == "09991234567"

bot.set_setting("card_number", "6037991234567890")
bot.set_setting("card_holder", "تست فروشگاه")
say("تایید نهایی")
assert bot.get_chat(chat)["state"] == "await_receipt"
conn = bot.db()
order = conn.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 1").fetchone()
sizes = [r[0] for r in conn.execute("SELECT size FROM order_items WHERE order_id=? ORDER BY position", (order["id"],))]
conn.close()
assert sizes == ["2XL", "L"]
assert "6037991234567890" in sent[-1]

# «زدم» means the customer paid; it must never fuzzily trigger edit mode.
say("زدم")
assert bot.get_chat(chat)["state"] == "await_receipt"
assert "عکس رسید" in sent[-1]

# Explicit editing after finalization is blocked to avoid duplicate orders.
say("ویرایش")
assert bot.get_chat(chat)["state"] == "await_receipt"
assert "سفارش نهایی شده" in sent[-1]

# Regression for chats already stuck in the old edit_menu state: answer a side
# question, then let «هیچ کدوم» return to the receipt step.
bot.update_chat(chat, state="edit_menu", edit_return_state="")
say("جنسش چطوره؟")
assert bot.get_chat(chat)["state"] == "edit_menu"
assert "کیفیت" in sent[-1] or "جنس" in sent[-1]
say("هیچ کدوم")
assert bot.get_chat(chat)["state"] == "await_receipt"

say("کنسل")
assert bot.get_chat(chat)["state"] == "confirm_cancel"
say("بله لغو کن")
assert bot.get_chat(chat)["state"] == ""
conn = bot.db()
assert conn.execute("SELECT status FROM orders WHERE id=?", (order["id"],)).fetchone()[0] == "cancelled"
conn.close()

print("ORDER STATE REGRESSION: OK")
