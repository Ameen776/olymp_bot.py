import time
import requests
import numpy as np
from datetime import datetime
import hmac
import hashlib
import urllib.parse
from typing import Dict, List
from config import *

class BinanceSignalBot:
    def __init__(self):
        self.base_url = "https://api.binance.com"
        self.session = requests.Session()
        self.session.headers.update({
            'X-MBX-APIKEY': BINANCE_API_KEY
        })
    
    def get_klines(self, symbol: str, interval: str = '1m', limit: int = 100):
        endpoint = "/api/v3/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        response = self.session.get(self.base_url + endpoint, params=params)
        return response.json()
    
    def calculate_rsi(self, prices: List[float], period: int = 14):
        """حساب RSI بدون pandas"""
        if len(prices) < period + 1:
            return 50
        
        deltas = np.diff(prices)
        seed = deltas[:period]
        
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        
        for i in range(period, len(deltas)):
            delta = deltas[i]
            if delta > 0:
                up_val = delta
                down_val = 0
            else:
                up_val = 0
                down_val = -delta
            
            up = (up * (period - 1) + up_val) / period
            down = (down * (period - 1) + down_val) / period
        
        if down == 0:
            return 100
        
        rs = up / down
        return 100 - (100 / (1 + rs))
    
    def calculate_sma(self, prices: List[float], period: int):
        """حساب المتوسط المتحرك البسيط"""
        if len(prices) < period:
            return None
        return np.mean(prices[-period:])
    
    def analyze_signals(self, kline_data):
        """تحليل الإشارات بدون pandas"""
        if not kline_data or len(kline_data) < 20:
            return []
        
        # استخراج أسعار الإغلاق
        closes = [float(k[4]) for k in kline_data]  # الفهرس 4 هو سعر الإغلاق
        
        # حساب RSI
        rsi = self.calculate_rsi(closes)
        
        # حساب المتوسطات المتحركة
        sma_short = self.calculate_sma(closes, 12)
        sma_long = self.calculate_sma(closes, 26)
        
        signals = []
        
        # تحليل RSI
        if rsi > RSI_OVERBOUGHT:
            signals.append({
                'type': 'SELL',
                'indicator': 'RSI',
                'value': round(rsi, 2),
                'strength': 'STRONG' if rsi > 80 else 'MODERATE'
            })
        elif rsi < RSI_OVERSOLD:
            signals.append({
                'type': 'BUY',
                'indicator': 'RSI',
                'value': round(rsi, 2),
                'strength': 'STRONG' if rsi < 20 else 'MODERATE'
            })
        
        # تحليل المتوسطات المتحركة
        if sma_short and sma_long and len(closes) >= 26:
            prev_short = np.mean(closes[-13:-1]) if len(closes) > 13 else None
            prev_long = np.mean(closes[-27:-1]) if len(closes) > 27 else None
            
            if prev_short and prev_long:
                if sma_short > sma_long and prev_short <= prev_long:
                    signals.append({
                        'type': 'BUY',
                        'indicator': 'MA CROSS',
                        'value': f"SMA12: {sma_short:.4f}",
                        'strength': 'GOLDEN CROSS'
                    })
                elif sma_short < sma_long and prev_short >= prev_long:
                    signals.append({
                        'type': 'SELL',
                        'indicator': 'MA CROSS',
                        'value': f"SMA12: {sma_short:.4f}",
                        'strength': 'DEATH CROSS'
                    })
        
        # تحليل الشمعة الأخيرة
        latest = kline_data[-1]
        open_price = float(latest[1])
        close_price = float(latest[4])
        
        if close_price > open_price:
            signals.append({
                'type': 'BULLISH',
                'indicator': 'CANDLE',
                'value': round(close_price, 4),
                'strength': 'GREEN_CANDLE'
            })
        else:
            signals.append({
                'type': 'BEARISH',
                'indicator': 'CANDLE',
                'value': round(close_price, 4),
                'strength': 'RED_CANDLE'
            })
        
        return signals
    
    def send_telegram_alert(self, pair: str, signals: list, interval: int):
        """إرسال تنبيه عبر Telegram (نفس الكود السابق)"""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("❌ Telegram credentials missing")
            return
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"🚨 *إشارة تداول* 🚨\n\n"
        message += f"📈 *الزوج:* {pair}\n"
        message += f"⏰ *الفترة:* {interval} ثانية\n"
        message += f"🕐 *الوقت:* {timestamp}\n\n"
        
        if signals:
            message += "*الإشارات المكتشفة:*\n"
            for signal in signals:
                emoji = "🟢" if signal['type'] in ['BUY', 'BULLISH'] else "🔴"
                message += f"{emoji} *{signal['type']}* بواسطة {signal['indicator']}\n"
                message += f"   القيمة: {signal['value']}\n"
                message += f"   القوة: {signal['strength']}\n\n"
        else:
            message += "📭 *لا توجد إشارات قوية حالياً*\n\n"
        
        message += "⚠️ *تحذير:* هذه ليست نصيحة مالية\n"
        message += "تأكد من إجراء بحثك الخاص"
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        params = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }
        
        try:
            response = requests.post(url, params=params, timeout=10)
            if response.status_code == 200:
                print(f"✅ تم إرسال التنبيه لـ {pair}")
            else:
                print(f"❌ فشل إرسال التنبيه: {response.text}")
        except Exception as e:
            print(f"❌ خطأ في إرسال Telegram: {e}")
    
    def run(self):
        """تشغيل البوت"""
        print("🚀 بدأ تشغيل بوت إشارات Binance...")
        print(f"📊 الأزواج المتابعة: {list(TRADING_PAIRS.keys())}")
        print(f"⏰ الفترات الزمنية: {TIME_INTERVALS} ثانية")
        
        last_sent = {pair: {interval: 0 for interval in TIME_INTERVALS} 
                    for pair in TRADING_PAIRS.keys()}
        
        while True:
            current_time = time.time()
            
            for pair_name, binance_symbol in TRADING_PAIRS.items():
                try:
                    # الحصول على البيانات
                    klines_data = self.get_klines(binance_symbol, '1m', 30)
                    
                    if not klines_data:
                        continue
                    
                    # تحليل الإشارات
                    signals = self.analyze_signals(klines_data)
                    
                    # إرسال التنبيهات حسب الوقت
                    for interval in TIME_INTERVALS:
                        if current_time - last_sent[pair_name][interval] >= interval:
                            if signals:  # أرسل فقط إذا كانت هناك إشارات
                                self.send_telegram_alert(pair_name, signals, interval)
                                last_sent[pair_name][interval] = current_time
                                time.sleep(1)  # تأخير بسيط بين الرسائل
                
                except Exception as e:
                    print(f"❌ خطأ في {pair_name}: {str(e)[:100]}")
                    time.sleep(5)
                    continue
            
            # انتظار 1 ثانية قبل التكرار التالي
            time.sleep(1)

def main():
    bot = BinanceSignalBot()
    bot.run()

if __name__ == "__main__":
    main()
