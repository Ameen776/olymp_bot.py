import os
import requests
import time
import numpy as np

# =========================
# قراءة المفاتيح من Environment Variables
# =========================
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.environ.get("BINANCE_SECRET_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
# =========================

# ربط أسماء Olymp Trade مع Binance
PAIRS = {
    "Bitcoin OTC": "BTCUSDT",
    "Ethereum OTC": "ETHUSDT",
    "Litecoin OTC": "LTCUSDT",
    "Ripple OTC": "XRPUSDT",
    "Solana OTC": "SOLUSDT",
    "EUR/GBP OTC": "EURGBP",
    "EUR/CHF OTC": "EURCHF",
    "AUD/JPY OTC": "AUDJPY",
    "USD/CHF OTC": "USDCHF",
    "CAD/JPY OTC": "CADJPY"
}

# أوقات الصفقة الممكنة (يمكن التعديل لاحقًا في المتغير)
TIMEFRAMES = {
    "15 ثانية": "1m",
    "30 ثانية": "1m",
    "1 دقيقة": "1m"
}

# دالة جلب الشموع من Binance
def get_klines(symbol, interval="1m", limit=50):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    return requests.get(url, params=params).json()

# دالة حساب RSI
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

# دالة إرسال الإشارة لتيليجرام
def send_signal(asset, direction, duration, reason):
    msg = f"""
🚨 إشارة Olymp Trade (OTC)

الأصل: {asset}
الاتجاه: {direction}
الوقت: {duration}
الدخول: الآن

التحليل:
{reason}
"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    requests.post(url, data=data)

# دالة تحليل الأسعار لكل زوج
def analyze():
    for asset, symbol in PAIRS.items():
        try:
            klines = get_klines(symbol)
            closes = np.array([float(k[4]) for k in klines])
            r = rsi(closes)

            # إشارات UP/DOWN بناء على RSI
            if r < 30:
                send_signal(asset, "📈 UP", "30 ثانية", "RSI تشبع بيعي + ارتداد")
            elif r > 70:
                send_signal(asset, "📉 DOWN", "30 ثانية", "RSI تشبع شرائي + انعكاس")

        except Exception as e:
            print(f"Error analyzing {asset}: {e}")
            continue

# الحلقة الرئيسية للبوت
while True:
    analyze()
    time.sleep(60)