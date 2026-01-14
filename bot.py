import time
import requests
import hmac
import hashlib
import urllib.parse
import json
from datetime import datetime
from typing import Dict, List
from config import *

class SimpleBinanceBot:
    def __init__(self):
        self.base_url = "https://api.binance.com"
        self.session = requests.Session()
        self.session.headers.update({
            'X-MBX-APIKEY': BINANCE_API_KEY,
            'Content-Type': 'application/json'
        })
        print("✅ البوت بدأ التشغيل")
        print(f"📊 يتابع: {list(TRADING_PAIRS.keys())}")
        
    def get_klines_simple(self, symbol: str):
        """الحصول على بيانات بسيطة من Binance"""
        try:
            endpoint = "/api/v3/ticker/24hr"
            params = {'symbol': symbol}
            
            response = self.session.get(self.base_url + endpoint, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ خطأ في API: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ خطأ في الاتصال: {e}")
            return None
    
    def get_recent_trades(self, symbol: str):
        """الحصول على آخر الصفقات"""
        try:
            endpoint = "/api/v3/trades"
            params = {'symbol': symbol, 'limit': 10}
            
            response = self.session.get(self.base_url + endpoint, params=params, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return None
                
        except Exception:
            return None
    
    def analyze_market(self, market_data, trades_data):
        """تحليل السوق بشكل مبسط"""
        signals = []
        
        if not market_data:
            return signals
        
        try:
            # تحليل التغير في السعر
            price_change_percent = float(market_data.get('priceChangePercent', 0))
            current_price = float(market_data.get('lastPrice', 0))
            
            # إشارات بناء على التغير السعري
            if price_change_percent > PRICE_CHANGE_THRESHOLD:
                signals.append({
                    'type': 'BUY',
                    'indicator': 'PRICE_CHANGE',
                    'value': f"+{price_change_percent:.2f}%",
                    'strength': 'BULLISH_MOMENTUM'
                })
            elif price_change_percent < -PRICE_CHANGE_THRESHOLD:
                signals.append({
                    'type': 'SELL',
                    'indicator': 'PRICE_CHANGE',
                    'value': f"{price_change_percent:.2f}%",
                    'strength': 'BEARISH_MOMENTUM'
                })
            
            # تحليل حجم التداول
            volume = float(market_data.get('volume', 0))
            quote_volume = float(market_data.get('quoteVolume', 0))
            
            if volume > 0 and quote_volume > 1000000:  # حجم كبير
                signals.append({
                    'type': 'HIGH_VOLUME',
                    'indicator': 'VOLUME',
                    'value': f"${quote_volume:,.0f}",
                    'strength': 'ACTIVE_MARKET'
                })
            
            # تحليل آخر الصفقات
            if trades_data:
                buy_count = sum(1 for trade in trades_data if not trade.get('isBuyerMaker', True))
                sell_count = len(trades_data) - buy_count
                
                if buy_count > sell_count * 1.5:
                    signals.append({
                        'type': 'BUY',
                        'indicator': 'TRADE_FLOW',
                        'value': f"{buy_count}/{sell_count}",
                        'strength': 'BUYING_PRESSURE'
                    })
                elif sell_count > buy_count * 1.5:
                    signals.append({
                        'type': 'SELL',
                        'indicator': 'TRADE_FLOW',
                        'value': f"{sell_count}/{buy_count}",
                        'strength': 'SELLING_PRESSURE'
                    })
            
            # السعر الحالي
            signals.append({
                'type': 'PRICE',
                'indicator': 'CURRENT',
                'value': f"${current_price:,.2f}",
                'strength': 'MARKET_PRICE'
            })
            
        except Exception as e:
            print(f"❌ خطأ في التحليل: {e}")
        
        return signals
    
    def send_telegram(self, pair: str, signals: List[Dict], interval: int):
        """إرسال رسالة عبر Telegram"""
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print("⚠️ مفاتيح Telegram غير موجودة")
            return False
        
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            message = "📊 *تقرير تداول*\n\n"
            message += f"*الزوج:* {pair}\n"
            message += f"*الوقت:* {timestamp}\n"
            message += f"*الفاصل:* {interval} ثانية\n\n"
            
            if signals:
                message += "*📈 الإشارات:*\n"
                for signal in signals:
                    emoji = "🟢" if signal['type'] == 'BUY' else "🔴" if signal['type'] == 'SELL' else "📊"
                    message += f"{emoji} *{signal['type']}* - {signal['indicator']}\n"
                    message += f"   القيمة: {signal['value']}\n"
                    message += f"   القوة: {signal['strength']}\n\n"
            else:
                message += "*📭 لا توجد إشارات قوية حالياً*\n\n"
            
            message += "⚡ *البوت يعمل بنجاح*\n"
            message += "🔔 الإشعارات نشطة كل دقيقة\n\n"
            message += "⚠️ *تحذير:* للتجربة فقط\n"
            
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                print(f"✅ تم إرسال التقرير لـ {pair}")
                return True
            else:
                print(f"❌ فشل إرسال: {response.text[:100]}")
                return False
                
        except Exception as e:
            print(f"❌ خطأ في Telegram: {e}")
            return False
    
    def check_api_status(self):
        """فحص حالة API"""
        try:
            response = requests.get(f"{self.base_url}/api/v3/ping", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def run(self):
        """التشغيل الرئيسي"""
        print("🔍 فحص اتصال API...")
        
        if not self.check_api_status():
            print("❌ Binance API غير متاح")
            return
        
        print("✅ اتصال API نشط")
        
        # إرسال رسالة بدء التشغيل
        start_signals = [{
            'type': 'STARTUP',
            'indicator': 'BOT',
            'value': 'التشغيل بنجاح',
            'strength': 'ONLINE'
        }]
        self.send_telegram('BOT_STATUS', start_signals, 0)
        
        last_sent = {pair: 0 for pair in TRADING_PAIRS.keys()}
        
        print("\n🔄 بدأ مراقبة الأسواق...\n")
        
        while True:
            try:
                current_time = time.time()
                
                for pair_name, binance_symbol in TRADING_PAIRS.items():
                    # التحقق من الوقت المناسب للإرسال
                    time_since_last = current_time - last_sent.get(pair_name, 0)
                    
                    if time_since_last >= min(TIME_INTERVALS):
                        # جمع البيانات
                        market_data = self.get_klines_simple(binance_symbol)
                        trades_data = self.get_recent_trades(binance_symbol)
                        
                        # التحليل
                        signals = self.analyze_market(market_data, trades_data)
                        
                        # إرسال التقرير
                        if signals:
                            self.send_telegram(pair_name, signals, min(TIME_INTERVALS))
                        
                        last_sent[pair_name] = current_time
                        
                        print(f"📡 {pair_name}: تم التحليل - {len(signals)} إشارة")
                
                # انتظار 10 ثواني قبل التكرار التالي
                time.sleep(10)
                
            except KeyboardInterrupt:
                print("\n🛑 إيقاف البوت...")
                break
            except Exception as e:
                print(f"❌ خطأ غير متوقع: {e}")
                time.sleep(30)

def main():
    bot = SimpleBinanceBot()
    bot.run()

if __name__ == "__main__":
    main()
