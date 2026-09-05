import os
import tempfile

os.environ["BOT_TOKEN"] = "dummy"
os.environ["ADMIN_ID"] = "0"
os.environ["SPAM_ENABLED"] = "1"
os.environ["SPAM_MESSAGE_LIMIT"] = "15"
os.environ["SPAM_WINDOW_SECONDS"] = "60"
os.environ["SPAM_MAX_WARNINGS"] = "3"

import main as bot

fd, path = tempfile.mkstemp(prefix="shop_antispam_", suffix=".db")
os.close(fd)
os.unlink(path)
bot.DB_PATH = path
bot.init_db()
chat_id = 123456
bot.ensure_chat(chat_id, "bc-test")

sent = []
bot.send_business = lambda connection_id, cid, text: sent.append((connection_id, cid, text))
bot.ADMIN_ID = 0

for warning_no in (1, 2, 3):
    for i in range(14):
        assert bot.anti_spam_check("bc-test", chat_id) is False
    assert bot.anti_spam_check("bc-test", chat_id) is True
    c = bot.get_chat(chat_id)
    assert int(c["spam_warnings"]) == warning_no
    if warning_no < 3:
        assert int(c["spam_blocked"]) == 0
    else:
        assert int(c["spam_blocked"]) == 1

assert len(sent) == 3, sent
assert "هشدار اسپم 1 از 3" in sent[0][2]
assert "هشدار اسپم 2 از 3" in sent[1][2]
assert "سومین هشدار" in sent[2][2]

# Once blocked, future messages are consumed silently.
before = len(sent)
assert bot.anti_spam_check("bc-test", chat_id) is True
assert len(sent) == before

bot.reset_spam_status(chat_id)
c = bot.get_chat(chat_id)
assert int(c["spam_warnings"]) == 0
assert int(c["spam_blocked"]) == 0
assert int(c["spam_message_count"]) == 0
print("ANTI-SPAM TESTS: 3/3 warnings, block, unblock/reset = OK")

try:
    os.unlink(path)
except FileNotFoundError:
    pass
