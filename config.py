import os

# Binance API Keys
BINANCE_API_KEY = os.environ.get('BINANCE_API_KEY', '')
BINANCE_SECRET_KEY = os.environ.get('BINANCE_SECRET_KEY', '')

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

# Trading Pairs Configuration (اختر واحداً فقط للبداية)
TRADING_PAIRS = {
    'BTCOTC': 'BTCUSDT'  # ابدأ بواحد فقط
}

# Timeframes for signal checking (in seconds)
TIME_INTERVALS = [60]  # ابدأ بـ 60 ثانية فقط

# Signal Thresholds
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
PRICE_CHANGE_THRESHOLD = 0.5  # 0.5%
VOLUME_SPIKE_MULTIPLIER = 2.0
