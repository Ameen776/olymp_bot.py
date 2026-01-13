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

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# =========================
# الزوج المختار (افتراضي)
# =========================
selected_pair = {"symbol": "BTC", "name": "Bitcoin OTC"}

# =========================
# جلب بيانات الأسعار (CryptoCompare)
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
        f"{API_URL}/sendMessage",
        data={"chat_id": CHAT_ID, "text": text},
        timeout=10
    )

def get_updates(offset=None):
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    r = requests.get(f"{API_URL}/getUpdates", params=params, timeout=35)
    return r.json()

# =========================
# تحليل الزوج المختار فقط
# =========================
def analyze_pair():
    klines = get_klines(selected_pair["symbol"])
    if not klines or len(klines) < 20:
        send("⚠️ بيانات غير كافية للتحليل")
        return

    closes = [float(k["close"]) for k in klines if "close" in k]
    r = rsi(np.array(closes))

    if r is None:
        send("⚠️ لم يتم حساب RSI")
        return

    if r < 30:
        send(
            f"🚨 إشارة تداول\n\n"
            f"الأصل: {selected_pair['name']}\n"
            f"الاتجاه: 📈 UP\n"
            f"الوقت: 30 ثانية\n\n"
            f"السبب: تشبع بيعي (RSI = {round(r,2)})"
        )
    elif r > 70:
        send(
            f"🚨 إشارة تداول\n\n"
            f"الأصل: {selected_pair['name']}\n"
            f"الاتجاه: 📉 DOWN\n"
            f"الوقت: 30 ثانية\n\n"
            f"السبب: تشبع شرائي (RSI = {round(r,2)})"
        )
    else:
        send(f"ℹ️ لا يوجد تشبع حاليًا (RSI = {round(r,2)})")

# =========================
# أوامر تيليجرام
# =========================
def handle_command(text):
    global selected_pair

    if text.startswith("/start"):
        send(
            "✅ البوت جاهز\n\n"
            "📌 الأوامر:\n"
            "/pair BTC\n"
            "/pair ETH\n"
            "/check\n"
            "/status"
        )

    elif text.startswith("/pair"):
        parts = text.split()
        if len(parts) == 2:
            symbol = parts[1].upper()
            selected_pair = {
                "symbol": symbol,
                "name": f"{symbol} OTC"
            }
            send(f"✅ تم اختيار الزوج: {symbol}")
        else:
            send("❌ استخدم: /pair BTC")

    elif text.startswith("/status"):
        send(f"📊 الزوج الحالي: {selected_pair['name']}")

    elif text.startswith("/check"):
        analyze_pair()

# =========================
# تشغيل البوت (Polling)
# =========================
def run_bot():
    send("🤖 تم تشغيل البوت")
    offset = None

    while True:
        updates = get_updates(offset)
        for update in updates.get("result", []):
            offset = update["update_id"] + 1
            message = update.get("message")
            if not message:
                continue
            text = message.get("text", "")
            handle_command(text)
        time.sleep(2)

# =========================
if __name__ == "__main__":
    run_bot()
