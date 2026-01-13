import os
import time
import requests
import threading
import numpy as np

# =======================
# Environment Variables
# =======================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# =======================
# أزواج Olymp Trade (نفس الكتابة)
# =======================
PAIRS = {
    "Bitcoin OTC": "BTCUSDT",
    "Ethereum OTC": "ETHUSDT",
    "Litecoin OTC": "LTCUSDT",
    "Ripple OTC": "XRPUSDT",
    "Solana OTC": "SOLUSDT",

    "NZD/USD OTC": "NZDUSDT",
    "USD/CHF OTC": "USDCHF",
    "AUD/CAD OTC": "AUDCAD",
    "AUD/CHF OTC": "AUDCHF",
    "AUD/JPY OTC": "AUDJPY",
    "AUD/NZD OTC": "AUDNZD",

    "CAD/CHF OTC": "CADCHF",
    "CAD/JPY OTC": "CADJPY",
    "CHF/JPY OTC": "CHFJPY",

    "EUR/AUD OTC": "EURAUD",
    "EUR/CAD OTC": "EURCAD",
    "EUR/CHF OTC": "EURCHF",
    "EUR/GBP OTC": "EURGBP"
}

selected_pair = None
running = False

# =======================
# Telegram helpers
# =======================
def send_message(text, keyboard=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "reply_markup": keyboard
    }
    requests.post(url, json=payload)

def send_pairs_buttons():
    keyboard = {
        "inline_keyboard": [
            [{"text": pair, "callback_data": pair}]
            for pair in PAIRS.keys()
        ]
    }
    send_message("📊 اختر الزوج (مطابق لأوليمب تريد):", keyboard)

# =======================
# Market Data
# =======================
def get_klines(symbol, interval="1m", limit=50):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    return requests.get(url, params=params).json()

def rsi(closes, period=14):
    deltas = np.diff(closes)
    gain = np.maximum(deltas, 0)
    loss = np.abs(np.minimum(deltas, 0))
    avg_gain = np.mean(gain[-period:])
    avg_loss = np.mean(loss[-period:])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# =======================
# Signal Loop
# =======================
def signal_loop():
    global running
    while running:
        try:
            symbol = PAIRS[selected_pair]
            klines = get_klines(symbol)
            closes = np.array([float(k[4]) for k in klines])
            r = rsi(closes)

            if r < 30:
                send_message(
                    f"📈 BUY\n"
                    f"الأصل: {selected_pair}\n"
                    f"RSI: {round(r,2)}\n"
                    f"الدخول: الآن\n"
                    f"المدة: 30 ثانية"
                )

            elif r > 70:
                send_message(
                    f"📉 SELL\n"
                    f"الأصل: {selected_pair}\n"
                    f"RSI: {round(r,2)}\n"
                    f"الدخول: الآن\n"
                    f"المدة: 30 ثانية"
                )

        except Exception as e:
            print("Error:", e)

        time.sleep(60)

# =======================
# Telegram Listener
# =======================
def listen_updates():
    global selected_pair, running
    offset = 0

    while True:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        r = requests.get(url, params={"offset": offset}).json()

        for update in r.get("result", []):
            offset = update["update_id"] + 1

            if "callback_query" in update:
                selected_pair = update["callback_query"]["data"]
                running = True
                send_message(
                    f"✅ تم اختيار:\n{selected_pair}\n"
                    f"سيتم إرسال إشارات BUY / SELL تلقائيًا"
                )
                threading.Thread(target=signal_loop, daemon=True).start()

        time.sleep(2)

# =======================
# Start
# =======================
send_pairs_buttons()
listen_updates()
