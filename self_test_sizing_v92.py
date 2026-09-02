import os, tempfile, sys
os.environ['BOT_TOKEN']='TEST_TOKEN'
os.environ['ADMIN_ID']='1'
os.environ['DB_PATH']=os.path.join(tempfile.gettempdir(),'shop_v92_sizing_test.db')
try: os.remove(os.environ['DB_PATH'])
except FileNotFoundError: pass
sys.path.insert(0, os.path.dirname(__file__))
import main as bot
bot.init_db()

aliases = {
    'S':'S','اسمال':'S','M':'M','مدیوم':'M','L':'L','لارج':'L',
    'XL':'XL','ایکس لارج':'XL','XXL':'2XL','2XL':'2XL','دو ایکس لارجم':'2XL',
    'XXXL':'3XL','3XL':'3XL','سه ایکس لارج':'3XL','4XL':'4XL','چهار ایکس لارج':'4XL'
}
print('SIZE ALIAS TESTS')
ok=0
for text,want in aliases.items():
    got=bot.extract_explicit_size(text)
    passed=got==want
    ok+=passed
    print(('OK' if passed else 'FAIL'), '|', text, '=>', got)

recommendations = [
    (165,80,'regular','outerwear','XL'),
    (165,80,'loose','outerwear','2XL'),
    (180,60,'regular','top','M'),
    (190,95,'regular','outerwear','3XL'),
    (175,120,'regular','outerwear','4XL'),
]
print('\nRECOMMENDATION TESTS')
rok=0
for h,w,fit,ptype,want in recommendations:
    got=bot.recommend_size(h,w,fit,ptype)
    passed=got==want
    rok+=passed
    print(('OK' if passed else 'FAIL'), '|', h,w,fit,ptype, '=>', got)

# Checkout must accept every size.
bot.send_business=lambda cid,chat,text: None
bot.send_admin=lambda text: None
chat=990001
bot.ensure_chat(chat,'biz')
accepted=0
for size in bot.SIZE_ORDER:
    bot.update_chat(chat,state='await_size',size='')
    bot.handle_business_message({'business_connection_id':'biz','chat':{'id':chat},'from':{'id':999},'text':size},business_owner_id=111)
    row=bot.get_chat(chat)
    passed=(row['size']==size and row['state']=='await_name')
    accepted+=passed
    print(('OK' if passed else 'FAIL'), '| checkout', size, '=>', row['size'], row['state'])

print(f'\nSUMMARY aliases={ok}/{len(aliases)} recommendations={rok}/{len(recommendations)} checkout={accepted}/{len(bot.SIZE_ORDER)}')
if ok != len(aliases) or rok != len(recommendations) or accepted != len(bot.SIZE_ORDER):
    raise SystemExit(1)
