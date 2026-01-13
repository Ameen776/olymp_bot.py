import os
import requests
import numpy as np

# =========================
# Environment Variables
# =========================
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# تحقق من المتغيرات
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise Exception("❌ تأكد من إضافة TELEGRAM_BOT_TOKEN و TELEGRAM_CHAT_ID في Render")

# =========================
# أزواج مدعومة فعليًا من Binance
# =========================
PAIRS = {
    "Bitcoin OTC": "BTCUSDT",
    "Ethereum OTC": "ETHUSDT",
    "Litecoin OTC": "LTCUSDT",
    "Ripple OTC": "XRPUSDT",
    "Solana OTC": "SOLUSDT"
}

# =========================
# جلب الشموع من Binance
# =========================
def get_klines(symbol, interval="1m", limit=50):
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

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
# إرسال إشارة تيليجرام
# =========================
def send_signal(asset, direction, duration, reason):
    message = f"""
🚨 إشارة تداول (OTC)

الأصل: {asset}
الاتجاه: {direction}
المدة: {duration}
الدخول: الآن

📊 التحليل:
{reason}
"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    requests.post(url, data=payload, timeout=10)

# =========================
# التحليل الرئيسي (بدون Loop)
# =========================
def analyze():
    for asset, symbol in PAIRS.items():
        try:
            klines = get_klines(symbol)

            # تحقق من صحة البيانات
            if not isinstance(klines, list) or len(klines) < 20:
                print(f"⚠️ بيانات غير كافية لـ {asset}")
                continue

            closes = []
            for k in klines:
                if isinstance(k, list) and len(k) > 4:
                    closes.append(float(k[4]))

            if len(closes) < 15:
                print(f"⚠️ شموع غير كافية لـ {asset}")
                continue

            closes = np.array(closes)
            r = rsi(closes)

            if r is None:
                continue

            if r < 30:
                send_signal(asset, "📈 UP", "30 ثانية", "RSI تشبع بيعي + احتمال ارتداد")
            elif r > 70:
                send_signal(asset, "📉 DOWN", "30 ثانية", "RSI تشبع شرائي + احتمال انعكاس")

        except Exception as e:
            print(f"❌ خطأ في {asset}: {e}")

# =========================
# تشغيل مرة واحدة (متوافق مع Render)
# =========================
if __name__ == "__main__":
    analyze()
