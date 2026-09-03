import os
os.environ["SPAM_ENABLED"] = "0"
import main
cases = [
('بچگانه موجوده ؟','بچگانه'),('برای بچه هم میشه استفاده کرد؟','بچه'),('چه سایزایی واسه بچه میخوره؟','قد و وزن'),('ببخشید این کارا دخترونست یا پسرونه؟','دختر'),('اسپرته این کارا؟','اسپرت'),('کیفیت کار چطوره؟','بالاست'),('واسه پاییز مناسبه؟','برای پاییز مناسبه'),('زمستون میشه پوشید؟','برای زمستون مناسبه'),('تابستون خوبه؟','برای تابستون مناسبه'),('بهار چطوره؟','برای بهار مناسبه')]
ok=0
for q,needle in cases:
 a=main.store_policy_answer(q) or ''; passed=needle in a; print(('OK' if passed else 'FAIL'),q,'=>',a); ok+=passed
print('SUMMARY',ok,'/',len(cases)); assert ok==len(cases)
assert main.extract_explicit_size('اسم مدلشو نمیپرسی؟') is None
assert main.extract_explicit_size('اسم مدلشو نمیدونم') is None
print('REGRESSION اسم/S: OK')
