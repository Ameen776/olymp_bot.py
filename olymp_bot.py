import os
import requests
import numpy as np

# =========================
# Telegram Environment Variables
# =========================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise Exception("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")

# =========================
# أزواج ثابتة (لا تعدلها)
# =========================
PAIRS = {
    "Bitcoin OTC": "BTC",
    "Ethereum OTC": "ETH",
    "Litecoin OTC": "LTC",
    "Ripple OTC": "XRP",
    "Solana OTC": "SOL"
}

# =========================
# جلب بيانات الأسعار (بديل Binance – يعمل على Render)
# =========================
def get_klines(symbol, limit=50):
    url = "https://min-api.cryptocompare.com/data/v2/histominute"
    params = {
        "fsym": symbol,
        "tsym": "USDT",
        "limit": limit
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    if data.get("Response") != "Success":
        return []

    return data["Data"]["Data"]

# =========================
# حساب RSI (آمن)
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
# إرسال رسالة تيليجرام
# =========================
def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }
    requests.post(url, data=payload, timeout=10)

# =========================
# التحليل
# =========================
def analyze():
    signals_sent = 0

    for asset, symbol in PAIRS.items():
        try:
            klines = get_klines(symbol)

            if not klines or len(klines) < 20:
                continue

            closes = [float(k["close"]) for k in klines if "close" in k]

            if len(closes) < 15:
                continue

            closes = np.array(closes)
            r = rsi(closes)

            if r is None:
                continue

            if r < 30:
                send_message(
                    f"🚨 إشارة تداول\n\n"
                    f"الأصل: {asset}\n"
                    f"الاتجاه: 📈 UP\n"
                    f"المدة: 30 ثانية\n\n"
                    f"التحليل:\nRSI تشبع بيعي"
                )
                signals_sent += 1

            elif r > 70:
                send_message(
                    f"🚨 إشارة تداول\n\n"
                    f"الأصل: {asset}\n"
                    f"الاتجاه: 📉 DOWN\n"
                    f"المدة: 30 ثانية\n\n"
                    f"التحليل:\nRSI تشبع شرائي"
                )
                signals_sent += 1

        except Exception as e:
            send_message(f"⚠️ خطأ في تحليل {asset}\n{e}")

    if signals_sent == 0:
        send_message("ℹ️ لا توجد فرص تداول آمنة حاليًا")

# =========================
# تشغيل مرة واحدة (متوافق مع Render)
# =========================
if __name__ == "__main__":
    analyze()
