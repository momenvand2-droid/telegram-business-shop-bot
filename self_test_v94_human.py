import main
cases = [
('بچگانه موجوده ؟','بچگانه'),('برای بچه هم میشه استفاده کرد؟','بچه'),('چه سایزایی واسه بچه میخوره؟','قد و وزن'),('ببخشید این کارا دخترونست یا پسرونه؟','دختر'),('اسپرته این کارا؟','اسپرت'),('کیفیت کار چطوره؟','بالاست'),('واسه پاییز مناسبه؟','برای پاییز مناسبه'),('زمستون میشه پوشید؟','برای زمستون مناسبه'),('تابستون خوبه؟','برای تابستون مناسبه'),('بهار چطوره؟','برای بهار مناسبه')]
ok=0
for q,needle in cases:
 a=main.store_policy_answer(q) or ''; passed=needle in a; print(('OK' if passed else 'FAIL'),q,'=>',a); ok+=passed
print('SUMMARY',ok,'/',len(cases)); assert ok==len(cases)
assert main.extract_explicit_size('اسم مدلشو نمیپرسی؟') is None
assert main.extract_explicit_size('اسم مدلشو نمیدونم') is None
assert not main.is_cancel_order_request('امکان لغو سفارش هست؟')
assert main.is_cancel_order_request('لطفا سفارشم رو کنسل کن')
print('REGRESSION اسم/S: OK')

# Side questions must be answered without consuming or changing the active
# checkout field. The handler should then repeat the exact pending prompt.
import tempfile
import os

with tempfile.TemporaryDirectory() as tmp:
 os.environ['DB_PATH'] = os.path.join(tmp, 'state_test.db')
 main.DB_PATH = os.environ['DB_PATH']
 main.init_db()
 sent=[]
 original_send = main.send_business
 original_admin = main.send_admin
 main.send_business = lambda connection_id, chat_id, text: sent.append(text)
 main.send_admin = lambda text: None
 try:
  state_cases = [
   ('await_product_count', 'هزینه ارسال چقدره؟', 'تعداد محصول'),
   ('await_item_name', 'آبرفت داره', 'اسم محصول شماره'),
   ('await_add_count', 'جنسش چطوره؟', 'تعداد محصول های جدید'),
   ('await_size', 'چند روزه میرسه؟', 'سایز هودی تست'),
   ('await_height_weight', 'مرجوعی دارین؟', 'قد و وزنت رو بفرست'),
   ('await_name', 'چه رنگایی دارین؟', 'اسم و فامیلی'),
   ('await_phone', 'هزینه پست چنده؟', 'شماره موبایل'),
   ('await_address', 'اورجیناله؟', 'آدرس کامل'),
  ]
  for i, (state, question, resume_needle) in enumerate(state_cases, 1001):
   main.ensure_chat(i, 'test-connection')
   main.update_chat(i, state=state, expected_items=2, collected_items=0)
   if state in {'await_size', 'await_height_weight'}:
    main.add_cart_item(i, 'هودی تست', 1)
   sent.clear()
   msg={'business_connection_id':'test-connection','chat':{'id':i},'from':{'id':i},'text':question}
   main.handle_business_message(msg)
   assert main.get_chat(i)['state'] == state, (state, question, main.get_chat(i)['state'])
   assert sent and resume_needle in main.normalize_text(sent[-1]), (state, question, sent)

  # Valid field values must still advance normally instead of being intercepted.
  i=2001
  main.ensure_chat(i, 'test-connection')
  main.update_chat(i, state='await_product_count')
  sent.clear()
  main.handle_business_message({'business_connection_id':'test-connection','chat':{'id':i},'from':{'id':i},'text':'2'})
  assert main.get_chat(i)['state'] == 'await_item_name'

  i=2002
  main.ensure_chat(i, 'test-connection')
  main.update_chat(i, state='await_item_name', expected_items=1, collected_items=0)
  main.handle_business_message({'business_connection_id':'test-connection','chat':{'id':i},'from':{'id':i},'text':'هودی مشکی'})
  assert main.get_chat(i)['state'] == 'confirm_cart'

  i=2003
  main.ensure_chat(i, 'test-connection')
  main.update_chat(i, state='await_address', full_name='علی رضایی', phone='09123456789', size='L')
  main.add_cart_item(i, 'هودی مشکی', 1)
  main.set_cart_item_size(i, 1, 'L')
  main.set_setting('card_number', '6037991234567890')
  main.set_setting('card_holder', 'صاحب کارت تست')
  sent.clear()
  main.handle_business_message({'business_connection_id':'test-connection','chat':{'id':i},'from':{'id':i},'text':'تهران، خیابان اداره پست، پلاک 2'})
  assert main.get_chat(i)['state'] == 'confirm_order'
  assert '6037991234567890' not in sent[-1]
  main.handle_business_message({'business_connection_id':'test-connection','chat':{'id':i},'from':{'id':i},'text':'تأیید نهایی'})
  assert main.get_chat(i)['state'] == 'await_receipt'
  assert '6037991234567890' in sent[-1]

  # Every cart line receives its own size before personal information starts.
  i=2004
  main.ensure_chat(i, 'test-connection')
  main.update_chat(i, state='await_size')
  main.add_cart_item(i, 'هودی مشکی', 1)
  main.add_cart_item(i, 'تیشرت سفید', 1)
  main.handle_business_message({'business_connection_id':'test-connection','chat':{'id':i},'from':{'id':i},'text':'L'})
  assert main.get_chat(i)['state'] == 'await_size'
  assert [r['size'] for r in main.cart_items(i)] == ['L', '']
  main.handle_business_message({'business_connection_id':'test-connection','chat':{'id':i},'from':{'id':i},'text':'XL'})
  assert main.get_chat(i)['state'] == 'await_name'
  assert [r['size'] for r in main.cart_items(i)] == ['L', 'XL']

  # Suggested size is recorded only after customer confirmation.
  i=2005
  main.ensure_chat(i, 'test-connection')
  main.update_chat(i, state='await_size')
  main.add_cart_item(i, 'دورس', 1)
  main.handle_business_message({'business_connection_id':'test-connection','chat':{'id':i},'from':{'id':i},'text':'قد 180 وزن 80'})
  pending = main.get_chat(i)['pending_size']
  assert pending and main.cart_items(i)[0]['size'] == ''
  main.handle_business_message({'business_connection_id':'test-connection','chat':{'id':i},'from':{'id':i},'text':'بله'})
  assert main.cart_items(i)[0]['size'] == pending

  # Explicit cancellation must work from every checkout state and clear data.
  cancel_states = [
   'await_product_count', 'await_item_name', 'confirm_cart', 'await_add_count',
   'await_size', 'await_height_weight', 'await_name', 'await_phone',
   'await_address', 'await_receipt',
  ]
  for i, state in enumerate(cancel_states, 3001):
   main.ensure_chat(i, 'test-connection')
   main.update_chat(
    i, state=state, product='هودی', size='L', full_name='علی رضایی',
    phone='09123456789', address='تهران خیابان تست پلاک 1',
    last_price=900000, expected_items=2, collected_items=1,
   )
   main.add_cart_item(i, 'هودی مشکی', 1)
   sent.clear()
   main.handle_business_message({
    'business_connection_id':'test-connection','chat':{'id':i},
    'from':{'id':i},'text':'لطفا سفارشم رو کنسل کن',
   })
   assert main.get_chat(i)['state'] == 'confirm_cancel', state
   assert main.cart_items(i), state
   main.handle_business_message({
    'business_connection_id':'test-connection','chat':{'id':i},
    'from':{'id':i},'text':'بله',
   })
   chat = main.get_chat(i)
   assert chat['state'] == '', (state, chat['state'])
   assert not main.cart_items(i), state
   assert not any(chat[field] for field in ('product','size','full_name','phone','address')), state
   assert sent and 'کامل کنسل شد' in sent[-1], (state, sent)

  # Bare «نه» in cart confirmation retains its old finalize-cart behavior.
  i=4001
  main.ensure_chat(i, 'test-connection')
  main.update_chat(i, state='confirm_cart')
  main.add_cart_item(i, 'تیشرت سفید', 1)
  main.handle_business_message({
   'business_connection_id':'test-connection','chat':{'id':i},
   'from':{'id':i},'text':'نه',
  })
  assert main.get_chat(i)['state'] == 'await_size'

  # Rejecting cancellation restores the exact previous state and cart.
  i=4003
  main.ensure_chat(i, 'test-connection')
  main.update_chat(i, state='await_phone')
  main.add_cart_item(i, 'هودی طوسی', 1)
  main.handle_business_message({'business_connection_id':'test-connection','chat':{'id':i},'from':{'id':i},'text':'سفارشم رو لغو کن'})
  main.handle_business_message({'business_connection_id':'test-connection','chat':{'id':i},'from':{'id':i},'text':'نه'})
  assert main.get_chat(i)['state'] == 'await_phone'
  assert main.cart_items(i)

  # Mid-order editing can change a selected product size and return to review.
  i=4004
  main.ensure_chat(i, 'test-connection')
  main.update_chat(
   i, state='confirm_order', full_name='علی رضایی', phone='09123456789',
   address='تهران خیابان تست پلاک 1',
  )
  main.add_cart_item(i, 'هودی', 1)
  main.add_cart_item(i, 'تیشرت', 2)
  main.set_cart_item_size(i, 1, 'L')
  main.set_cart_item_size(i, 2, 'M')
  main.handle_business_message({'business_connection_id':'test-connection','chat':{'id':i},'from':{'id':i},'text':'ویرایش سفارش'})
  assert main.get_chat(i)['state'] == 'edit_menu'
  main.handle_business_message({'business_connection_id':'test-connection','chat':{'id':i},'from':{'id':i},'text':'3'})
  main.handle_business_message({'business_connection_id':'test-connection','chat':{'id':i},'from':{'id':i},'text':'2'})
  main.handle_business_message({'business_connection_id':'test-connection','chat':{'id':i},'from':{'id':i},'text':'2XL'})
  assert main.get_chat(i)['state'] == 'confirm_order'
  assert main.cart_item(i, 2)['size'] == '2XL'
  main.handle_business_message({'business_connection_id':'test-connection','chat':{'id':i},'from':{'id':i},'text':'تعداد رو تغییر بده'})
  assert main.get_chat(i)['state'] == 'edit_quantity_target'
  main.handle_business_message({'business_connection_id':'test-connection','chat':{'id':i},'from':{'id':i},'text':'1'})
  main.handle_business_message({'business_connection_id':'test-connection','chat':{'id':i},'from':{'id':i},'text':'3'})
  assert main.get_chat(i)['state'] == 'confirm_order'
  assert main.cart_item(i, 1)['quantity'] == 3
  main.handle_business_message({'business_connection_id':'test-connection','chat':{'id':i},'from':{'id':i},'text':'آدرسم رو عوض کن'})
  assert main.get_chat(i)['state'] == 'edit_address'
  main.handle_business_message({'business_connection_id':'test-connection','chat':{'id':i},'from':{'id':i},'text':'کرج خیابان آزادی پلاک 20'})
  assert main.get_chat(i)['state'] == 'confirm_order'
  assert 'کرج' in main.get_chat(i)['address']
  main.handle_business_message({'business_connection_id':'test-connection','chat':{'id':i},'from':{'id':i},'text':'این محصول رو حذف کن'})
  main.handle_business_message({'business_connection_id':'test-connection','chat':{'id':i},'from':{'id':i},'text':'2'})
  assert main.get_chat(i)['state'] == 'confirm_order'
  assert len(main.cart_items(i)) == 1

  # A registered order waiting for payment/receipt is marked cancelled too.
  i=4002
  main.ensure_chat(i, 'test-connection')
  main.update_chat(i, state='await_receipt')
  conn = main.db()
  cur = conn.execute(
   "INSERT INTO orders(chat_id,status,created_at) VALUES(?,?,?)",
   (i, 'awaiting_receipt', '2026-09-02T00:00:00'),
  )
  order_id = cur.lastrowid
  conn.commit()
  conn.close()
  main.handle_business_message({
   'business_connection_id':'test-connection','chat':{'id':i},
   'from':{'id':i},'text':'لغوش کن',
  })
  assert main.get_chat(i)['state'] == 'confirm_cancel'
  main.handle_business_message({
   'business_connection_id':'test-connection','chat':{'id':i},
   'from':{'id':i},'text':'بله',
  })
  conn = main.db()
  status = conn.execute('SELECT status FROM orders WHERE id=?', (order_id,)).fetchone()['status']
  conn.close()
  assert status == 'cancelled_by_customer'
 finally:
  main.send_business = original_send
  main.send_admin = original_admin
print('REGRESSION side-question/state-resume: OK')
