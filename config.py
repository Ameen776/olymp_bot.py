import os

# Binance API Keys
BINANCE_API_KEY = os.environ.get('BINANCE_API_KEY', '')
BINANCE_SECRET_KEY = os.environ.get('BINANCE_SECRET_KEY', '')

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

# Trading Pairs Configuration
TRADING_PAIRS = {
    'BTCOTC': 'BTCUSDT',
    'XRPOTC': 'XRPUSDT',
    'SOLOTC': 'SOLUSDT',
    'AUDCADOTC': 'AUDCAD'
}

# Timeframes for signal checking (in seconds)
TIME_INTERVALS = [15, 30, 45, 60]

# Signal Thresholds (يمكنك تعديلها)
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
MACD_SIGNAL_THRESHOLD = 0
