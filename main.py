import os
import time
import requests

TOKEN = os.environ["BOT_TOKEN"]
API = f"https://api.telegram.org/bot{TOKEN}"

def api(method, data=None):
    r = requests.post(f"{API}/{method}", data=data or {}, timeout=60)
    r.raise_for_status()
    result = r.json()
    if not result.get("ok"):
        raise RuntimeError(result)
    return result["result"]

def main():
    offset = 0
    print("Telegram Business test bot is running...", flush=True)

    while True:
        try:
            updates = api("getUpdates", {
                "offset": offset,
                "timeout": 50,
                "allowed_updates": '["business_connection","business_message"]'
            })

            for update in updates:
                offset = update["update_id"] + 1

                if "business_connection" in update:
                    bc = update["business_connection"]
                    print(
                        f"Business connection: id={bc.get('id')} "
                        f"enabled={bc.get('is_enabled')}",
                        flush=True
                    )

                msg = update.get("business_message")
                if not msg:
                    continue

                # Ignore messages sent by the connected business account itself.
                if msg.get("sender_business_bot"):
                    continue

                connection_id = msg.get("business_connection_id")
                chat_id = msg["chat"]["id"]
                text = (msg.get("text") or "").strip()

                if not connection_id:
                    continue

                if text:
                    reply = (
                        "سلام 👋\n"
                        "اتصال ربات فروشگاه با اکانت تلگرام با موفقیت انجام شده ✅\n"
                        "این فعلاً پیام آزمایشی ماست."
                    )
                else:
                    reply = (
                        "پیامت دریافت شد ✅\n"
                        "اتصال ربات فروشگاه با اکانت تلگرام فعاله."
                    )

                api("sendMessage", {
                    "business_connection_id": connection_id,
                    "chat_id": chat_id,
                    "text": reply
                })

        except requests.RequestException as e:
            print("Network error:", e, flush=True)
            time.sleep(5)
        except Exception as e:
            print("Error:", repr(e), flush=True)
            time.sleep(5)

if __name__ == "__main__":
    main()
