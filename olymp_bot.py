import os
import time
import threading
import requests
import json
from collections import deque
from websocket import WebSocketApp

# ================== ENV ==================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ================== STATE ==================
user_state = {
    "symbol": None,
    "interval": None,  # seconds
    "ws": None,
    "prices": deque(maxlen=50),
    "last_signal": None,
}

# ================== UTILS ==================
def send_message(text, reply_markup=None):
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    requests.post(f"{TELEGRAM_API}/sendMessage", data=payload, timeout=5)

def rsi(prices, period=14):
    if len(prices) < period + 1:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(-period, 0):
        diff = prices[i] - prices[i - 1]
        if diff > 0:
            gains += diff
        else:
            losses -= diff
    if losses == 0:
        return 100
    rs = gains / losses
    return 100 - (100 / (1 + rs))

# ================== BINANCE WS ==================
def on_message(ws, message):
    data = json.loads(message)
    price = float(data["p"])
    user_state["prices"].append(price)

def on_error(ws, error):
    print("WS ERROR:", error)

def on_close(ws):
    print("WS CLOSED")

def start_ws(symbol):
    if user_state["ws"]:
        try:
            user_state["ws"].close()
        except:
            pass

    stream = f"{symbol.lower()}@trade"
    url = f"wss://stream.binance.com:9443/ws/{stream}"

    ws = WebSocketApp(
        url,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )

    user_state["ws"] = ws
    threading.Thread(target=ws.run_forever, daemon=True).start()

# ================== SIGNAL LOOP ==================
def signal_loop():
    while True:
        time.sleep(1)
        if not user_state["symbol"] or not user_state["interval"]:
            continue

        if len(user_state["prices"]) < 20:
            continue

        r = rsi(list(user_state["prices"]))
        if r is None:
            continue

        now = time.time()
        last = user_state.get("last_check", 0)
        if now - last < user_state["interval"]:
            continue
        user_state["last_check"] = now

        if r > 70 and user_state["last_signal"] != "SELL":
            send_message(
                f"🔴 SELL\n"
                f"زوج: {user_state['symbol']}\n"
                f"RSI: {r:.2f}"
            )
            user_state["last_signal"] = "SELL"

        elif r < 30 and user_state["last_signal"] != "BUY":
            send_message(
                f"🟢 BUY\n"
                f"زوج: {user_state['symbol']}\n"
                f"RSI: {r:.2f}"
            )
            user_state["last_signal"] = "BUY"

# ================== TELEGRAM ==================
def keyboard(rows):
    return {"keyboard": rows, "resize_keyboard": True}

def handle_update(update):
    if "message" not in update:
        return

    text = update["message"].get("text", "")

    if text == "/start":
        user_state["symbol"] = None
        user_state["interval"] = None
        send_message(
            "اختر الزوج:",
            keyboard([
                ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
                ["SOLUSDT", "XRPUSDT", "ADAUSDT"]
            ])
        )
        return

    if text.endswith("USDT"):
        user_state["symbol"] = text
        start_ws(text)
        send_message(
            f"✅ تم اختيار الزوج: {text}\nاختر مدة الإشارة:",
            keyboard([
                ["15 ثانية", "30 ثانية"],
                ["45 ثانية", "60 ثانية"]
            ])
        )
        return

    if "ثانية" in text:
        sec = int(text.split()[0])
        user_state["interval"] = sec
        user_state["last_signal"] = None
        send_message(
            f"⏱ تم الضبط على {sec} ثانية\n"
            f"📡 البوت يراقب السوق الآن ويرسل إشارات BUY / SELL تلقائيًا"
        )
        return

def telegram_loop():
    offset = None
    while True:
        try:
            resp = requests.get(
                f"{TELEGRAM_API}/getUpdates",
                params={"offset": offset, "timeout": 30},
                timeout=35,
            ).json()

            for upd in resp.get("result", []):
                offset = upd["update_id"] + 1
                handle_update(upd)

        except Exception as e:
            print("TG ERROR:", e)
            time.sleep(1)

# ================== MAIN ==================
if __name__ == "__main__":
    send_message("🤖 البوت شغّال\nاكتب /start")
    threading.Thread(target=signal_loop, daemon=True).start()
    telegram_loop()
