import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime
import hmac
import hashlib
import urllib.parse
from typing import Dict, Optional
from config import *

class BinanceSignalBot:
    def __init__(self):
        self.base_url = "https://api.binance.com"
        self.session = requests.Session()
        self.session.headers.update({
            'X-MBX-APIKEY': BINANCE_API_KEY
        })
        
    def generate_signature(self, params: Dict) -> str:
        """توقيع طلبات Binance API"""
        query_string = urllib.parse.urlencode(params)
        return hmac.new(
            BINANCE_SECRET_KEY.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def get_klines(self, symbol: str, interval: str = '1m', limit: int = 100):
        """الحصول على بيانات الشموع من Binance"""
        endpoint = "/api/v3/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        response = self.session.get(self.base_url + endpoint, params=params)
        return response.json()
    
    def calculate_indicators(self, data):
        """حساب المؤشرات الفنية"""
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        # تحويل الأنواع
        df['close'] = df['close'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        
        # حساب RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # حساب MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['histogram'] = df['macd'] - df['signal']
        
        return df
    
    def analyze_signals(self, df):
        """تحليل الإشارات"""
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        signals = []
        
        # RSI Signals
        if latest['rsi'] > RSI_OVERBOUGHT:
            signals.append({
                'type': 'SELL',
                'indicator': 'RSI',
                'value': round(latest['rsi'], 2),
                'strength': 'STRONG' if latest['rsi'] > 80 else 'MODERATE'
            })
        elif latest['rsi'] < RSI_OVERSOLD:
            signals.append({
                'type': 'BUY',
                'indicator': 'RSI',
                'value': round(latest['rsi'], 2),
                'strength': 'STRONG' if latest['rsi'] < 20 else 'MODERATE'
            })
        
        # MACD Signals
        if latest['macd'] > latest['signal'] and prev['macd'] <= prev['signal']:
            signals.append({
                'type': 'BUY',
                'indicator': 'MACD',
                'value': round(latest['macd'], 4),
                'strength': 'CROSSOVER'
            })
        elif latest['macd'] < latest['signal'] and prev['macd'] >= prev['signal']:
            signals.append({
                'type': 'SELL',
                'indicator': 'MACD',
                'value': round(latest['macd'], 4),
                'strength': 'CROSSOVER'
            })
        
        # Price Action
        if latest['close'] > latest['open']:
            signals.append({
                'type': 'BULLISH',
                'indicator': 'CANDLE',
                'value': round(latest['close'], 4),
                'strength': 'CLOSING_ABOVE_OPEN'
            })
        else:
            signals.append({
                'type': 'BEARISH',
                'indicator': 'CANDLE',
                'value': round(latest['close'], 4),
                'strength': 'CLOSING_BELOW_OPEN'
            })
        
        return signals
    
    def send_telegram_alert(self, pair: str, signals: list, interval: int):
        """إرسال تنبيه عبر Telegram"""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("❌ Telegram credentials missing")
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"🚨 *إشارة تداول* 🚨\n\n"
        message += f"📈 *الزوج:* {pair}\n"
        message += f"⏰ *الفترة:* {interval} ثانية\n"
        message += f"🕐 *الوقت:* {timestamp}\n\n"
        message += "*الإشارات المكتشفة:*\n"
        
        for signal in signals:
            emoji = "🟢" if signal['type'] in ['BUY', 'BULLISH'] else "🔴"
            message += f"{emoji} {signal['type']} بواسطة {signal['indicator']}\n"
            message += f"   القيمة: {signal['value']}\n"
            message += f"   القوة: {signal['strength']}\n\n"
        
        message += "⚠️ *تحذير:* هذه ليست نصيحة مالية\n"
        message += "تأكد من إجراء بحثك الخاص"
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        params = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        
        try:
            response = requests.post(url, params=params)
            if response.status_code == 200:
                print(f"✅ تم إرسال التنبيه لـ {pair}")
            else:
                print(f"❌ فشل إرسال التنبيه: {response.text}")
        except Exception as e:
            print(f"❌ خطأ في إرسال Telegram: {e}")
    
    def run(self):
        """تشغيل البوت الرئيسي"""
        print("🚀 بدأ تشغيل بوت إشارات Binance...")
        print(f"📊 الأزواج المتابعة: {list(TRADING_PAIRS.keys())}")
        print(f"⏰ الفترات الزمنية: {TIME_INTERVALS} ثانية")
        
        while True:
            for pair_name, binance_symbol in TRADING_PAIRS.items():
                try:
                    # الحصول على بيانات Binance
                    klines_data = self.get_klines(binance_symbol, '1m', 100)
                    
                    if not klines_data:
                        continue
                    
                    # حساب المؤشرات
                    df = self.calculate_indicators(klines_data)
                    
                    # تحليل الإشارات
                    signals = self.analyze_signals(df)
                    
                    # إرسال التنبيهات حسب الفترات الزمنية
                    current_second = datetime.now().second
                    
                    for interval in TIME_INTERVALS:
                        if current_second % interval == 0 and signals:
                            self.send_telegram_alert(pair_name, signals, interval)
                            time.sleep(1)  # منع إرسال متعدد
                
                except Exception as e:
                    print(f"❌ خطأ في معالجة {pair_name}: {e}")
                    continue
            
            # انتظار ثانية قبل التكرار
            time.sleep(1)

def main():
    """الدالة الرئيسية للتشغيل"""
    bot = BinanceSignalBot()
    bot.run()

if __name__ == "__main__":
    main()
