import os, tempfile
os.environ['BOT_TOKEN']='TEST_TOKEN'
os.environ['ADMIN_ID']='0'
os.environ['SPAM_ENABLED']='0'
os.environ['DB_PATH']=os.path.join(tempfile.gettempdir(),'shop_v98_receipt_lock.db')
try: os.remove(os.environ['DB_PATH'])
except FileNotFoundError: pass
import main as bot
bot.init_db()
bot.set_setting('card_number','1111222233334444')
bot.set_setting('card_holder','Old Holder')
chat=98001
bot.ensure_chat(chat,'biz')
# Before receipt: current card is visible.
a=bot.payment_text_for_chat(chat)
assert '1111222233334444' in a
# Change card before receipt: new current card must be visible.
bot.set_setting('card_number','5555666677778888')
bot.set_setting('card_holder','New Holder')
b=bot.payment_text_for_chat(chat)
assert '5555666677778888' in b and 'New Holder' in b
# Create waiting order and simulate receipt by persisted status.
conn=bot.db()
conn.execute("INSERT INTO orders(chat_id,product,size,full_name,phone,address,price,receipt_file_id,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,datetime('now'))",
             (chat,'هودی','XL','Test','09120000000','Tehran',1000000,'receipt-photo','receipt_sent'))
conn.commit(); conn.close()
# After receipt: no card number appears, even after another admin card change.
c=bot.payment_text_for_chat(chat)
assert '5555666677778888' not in c and 'رسید پرداختتون دریافت شده' in c
bot.set_setting('card_number','9999000011112222')
bot.set_setting('card_holder','Third Holder')
d=bot.payment_text_for_chat(chat)
assert '9999000011112222' not in d and 'رسید پرداختتون دریافت شده' in d
print('V9.8 receipt lock: OK')
