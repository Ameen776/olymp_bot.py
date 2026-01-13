import os
import requests
import numpy as np
import time

# =========================
# Telegram config
# =========================
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise Exception("Missing TELEGRAM config")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# =========================
# الأزواج المتاحة
# =========================
AVAILABLE_PAIRS = {
    "BTC": "Bitcoin OTC",
    "ETH": "Ethereum OTC",
    "LTC": "Litecoin OTC",
    "XRP": "Ripple OTC",
    "SOL": "Solana OTC"
}

# الزوج المختار (افتراضي)
selected_symbol = "BTC"
last_signal = None  # لمنع التكرار

# =========================
# جلب بيانات السوق (بديل Binance)
# =========================
def get_klines(symbol, limit=50):
    url = "https://min-api.cryptocompare.com/data/v2/histominute"
    params = {"fsym": symbol, "tsym": "USDT", "limit": limit}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    if data.get("Response") != "Success":
        return []
    return data["Data"]["Data"]

# =========================
# RSI
# =========================
def rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    deltas = np.diff(closes)
    gain = np.maximum(deltas, 0)
    loss = np.abs(np.minimum(deltas, 0))
    avg_gain = np.mean(gain[-period:])
    avg_loss = np.mean(loss[-period:])
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# =========================
# Telegram helpers
# =========================
def send(text):
    requests.post(
        f"{TG_API}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text},
        timeout=10
    )

def get_updates(offset=None):
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    r = requests.get(f"{TG_API}/getUpdates", params=params, timeout=35)
    return r.json()

# =========================
# تحليل تلقائي للزوج المختار
# =========================
def auto_analyze():
    global last_signal

    klines = get_klines(selected_symbol)
    if len(klines) < 20:
        return

    closes = np.array([k["close"] for k in klines])
    r = rsi(closes)
    if r is None:
        return

    pair_name = AVAILABLE_PAIRS[selected_symbol]

    if r < 30 and last_signal != "BUY":
        send(
            f"🚨 إشارة شراء\n\n"
            f"الأصل: {pair_name}\n"
            f"الوقت: الآن\n"
            f"المدة: 1 دقيقة\n\n"
            f"السبب: تشبع بيعي (RSI = {round(r,2)})"
        )
        last_signal = "BUY"

    elif r > 70 and last_signal != "SELL":
        send(
            f"🚨 إشارة بيع\n\n"
            f"الأصل: {pair_name}\n"
            f"الوقت: الآن\n"
            f"المدة: 1 دقيقة\n\n"
            f"السبب: تشبع شرائي (RSI = {round(r,2)})"
        )
        last_signal = "SELL"

# =========================
# أوامر التحكم
# =========================
def handle_command(text):
    global selected_symbol, last_signal

    if text == "/start":
        send(
            "🤖 البوت يعمل تلقائيًا\n\n"
            "اختر الزوج:\n"
            "/pair BTC\n"
            "/pair ETH\n"
            "/pair LTC\n"
            "/pair XRP\n"
            "/pair SOL"
        )

    elif text.startswith("/pair"):
        parts = text.split()
        if len(parts) == 2 and parts[1] in AVAILABLE_PAIRS:
            selected_symbol = parts[1]
            last_signal = None
            send(f"✅ تم اختيار الزوج: {AVAILABLE_PAIRS[selected_symbol]}")
        else:
            send("❌ زوج غير مدعوم")

# =========================
# تشغيل البوت (Auto + Commands)
# =========================
def run():
    send("✅ تم تشغيل البوت – مراقبة تلقائية")
    offset = None

    while True:
        try:
            # تحليل تلقائي
            auto_analyze()

            # استقبال أوامر
            updates = get_updates(offset)
            for u in updates.get("result", []):
                offset = u["update_id"] + 1
                msg = u.get("message", {})
                text = msg.get("text")
                if text:
                    handle_command(text)

            time.sleep(60)  # فحص كل دقيقة

        except Exception as e:
            send(f"⚠️ خطأ مؤقت: {e}")
            time.sleep(60)

# =========================
if __name__ == "__main__":
    run()
