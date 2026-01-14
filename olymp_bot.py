#!/usr/bin/env python3
"""
بوت إشارات تداول متكامل
يقرأ جميع المفاتيح من متغيرات Render
"""

import os
import time
import requests
import hmac
import hashlib
from datetime import datetime

# ================== قراءة جميع المفاتيح من Render ==================
# Binance API Keys
BINANCE_API_KEY = os.environ.get('BINANCE_API_KEY', '')
BINANCE_SECRET_KEY = os.environ.get('BINANCE_SECRET_KEY', '')

# Telegram Keys
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '')

# ================== إعدادات البوت ==================
TRADING_PAIRS = {
    'BTCOTC': 'BTCUSDT',
    'XRPOTC': 'XRPUSDT', 
    'SOLOTC': 'SOLUSDT',
    'AUDCADOTC': 'AUDCAD'
}

# إعدادات الوقت (بالثواني)
TIME_INTERVALS = [15, 30, 45, 60]

# ================== دوال Binance مع التواقيع ==================
def generate_binance_signature(params, secret_key):
    """توليد توقيع لطلبات Binance API"""
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    return hmac.new(
        secret_key.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

def get_binance_klines(symbol, interval='1m', limit=50):
    """الحصول على بيانات الشموع من Binance API"""
    try:
        endpoint = "https://api.binance.com/api/v3/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        headers = {'X-MBX-APIKEY': BINANCE_API_KEY} if BINANCE_API_KEY else {}
        
        response = requests.get(
            endpoint, 
            params=params, 
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ خطأ Binance API: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ خطأ في اتصال Binance: {e}")
        return None

def get_binance_ticker(symbol):
    """الحصول على بيانات السوق الحالية"""
    try:
        endpoint = "https://api.binance.com/api/v3/ticker/24hr"
        params = {'symbol': symbol}
        
        headers = {'X-MBX-APIKEY': BINANCE_API_KEY} if BINANCE_API_KEY else {}
        
        response = requests.get(
            endpoint, 
            params=params, 
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return None
            
    except Exception:
        return None

# ================== دوال Telegram ==================
def send_telegram_alert(pair_name, interval, signals, price_data=None):
    """إرسال تنبيه إلى Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ مفاتيح Telegram غير موجودة في متغيرات البيئة")
        return False
    
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # بناء الرسالة
        message = f"""
<b>🚨 إشارة تداول - {pair_name}</b>
━━━━━━━━━━━━━━━━━━━━
<b>⏰ الوقت:</b> {timestamp}
<b>⏱️ الفاصل:</b> كل {interval} ثانية
━━━━━━━━━━━━━━━━━━━━
"""
        
        # إضافة بيانات السعر إذا موجودة
        if price_data:
            message += f"""<b>💰 السعر الحالي:</b> ${float(price_data['lastPrice']):,.4f}
<b>📈 الأعلى 24h:</b> ${float(price_data['highPrice']):,.4f}
<b>📉 الأدنى 24h:</b> ${float(price_data['lowPrice']):,.4f}
<b>🔄 التغير 24h:</b> {float(price_data['priceChangePercent']):+.2f}%
<b>📊 الحجم 24h:</b> {float(price_data['volume']):,.0f}
━━━━━━━━━━━━━━━━━━━━
"""
        
        # إضافة الإشارات
        if signals:
            message += "<b>🎯 الإشارات المكتشفة:</b>\n"
            for signal in signals:
                emoji = "🟢" if signal['type'] == 'BUY' else "🔴"
                message += f"{emoji} <b>{signal['type']}</b> - {signal['reason']}\n"
                if 'value' in signal:
                    message += f"   📊 القيمة: {signal['value']}\n"
        else:
            message += "📭 <b>لا توجد إشارات قوية حالياً</b>\n"
        
        # التذييل
        message += """
━━━━━━━━━━━━━━━━━━━━
<b>🔐 المفاتيح:</b> ⬆️ من Render
<b>🤖 البوت:</b> ⚡ يعمل بنجاح
<b>⚠️ تنبيه:</b> هذه ليست نصيحة مالية
"""
        
        # إرسال الرسالة
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
        
        response = requests.post(url, json=data, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ تم إرسال إشعار {pair_name}")
            return True
        else:
            print(f"❌ فشل إرسال: {response.text[:100]}")
            return False
            
    except Exception as e:
        print(f"❌ خطأ في إرسال Telegram: {e}")
        return False

# ================== تحليل الإشارات ==================
def analyze_candle_pattern(klines):
    """تحليل نمط الشموع"""
    if not klines or len(klines) < 3:
        return []
    
    try:
        signals = []
        
        # الشمعة الحالية
        current = klines[-1]
        prev = klines[-2]
        prev_prev = klines[-3]
        
        # تحويل القيم
        cur_open = float(current[1])
        cur_close = float(current[4])
        cur_high = float(current[2])
        cur_low = float(current[3])
        
        prev_open = float(prev[1])
        prev_close = float(prev[4])
        
        prev_prev_open = float(prev_prev[1])
        prev_prev_close = float(prev_prev[4])
        
        # 1. شمعة صعودية قوية
        if cur_close > cur_open and (cur_close - cur_open) > (cur_high - cur_low) * 0.6:
            signals.append({
                'type': 'BUY',
                'reason': 'شمعة صعودية قوية',
                'value': f"{((cur_close - cur_open) / cur_open * 100):.2f}%"
            })
        
        # 2. شمعة هبوطية قوية
        elif cur_close < cur_open and (cur_open - cur_close) > (cur_high - cur_low) * 0.6:
            signals.append({
                'type': 'SELL',
                'reason': 'شمعة هبوطية قوية',
                'value': f"{((cur_open - cur_close) / cur_open * 100):.2f}%"
            })
        
        # 3. اختراق مقاومة
        if cur_high > max(float(k[2]) for k in klines[-10:-1]):
            signals.append({
                'type': 'BUY',
                'reason': 'اختراق مقاومة',
                'value': f"قمة جديدة: ${cur_high:.4f}"
            })
        
        # 4. اختراق دعم
        if cur_low < min(float(k[3]) for k in klines[-10:-1]):
            signals.append({
                'type': 'SELL',
                'reason': 'اختراق دعم',
                'value': f"قاع جديد: ${cur_low:.4f}"
            })
        
        return signals
        
    except Exception as e:
        print(f"❌ خطأ في تحليل الشموع: {e}")
        return []

def analyze_price_action(ticker_data):
    """تحليل حركة السعر"""
    if not ticker_data:
        return []
    
    try:
        signals = []
        
        price_change = float(ticker_data['priceChangePercent'])
        volume = float(ticker_data['volume'])
        
        # إشارات بناء على التغير السعري
        if price_change > 1.5:
            signals.append({
                'type': 'BUY',
                'reason': 'زخم صعودي قوي',
                'value': f"+{price_change:.2f}%"
            })
        elif price_change < -1.5:
            signals.append({
                'type': 'SELL',
                'reason': 'زخم هبوطي قوي',
                'value': f"{price_change:.2f}%"
            })
        
        # إشارات بناء على حجم التداول
        avg_volume = volume / 24  # متوسط حجم ساعي
        if avg_volume > 100000:  # حجم كبير
            signals.append({
                'type': 'HIGH_VOLUME',
                'reason': 'حجم تداول مرتفع',
                'value': f"${volume:,.0f}"
            })
        
        return signals
        
    except Exception:
        return []

# ================== دوال المساعدة ==================
def check_api_keys():
    """فحص المفاتيح في متغيرات البيئة"""
    print("🔍 فحص المفاتيح في متغيرات Render...")
    
    keys_status = {
        'Binance API Key': '✅ موجود' if BINANCE_API_KEY else '❌ مفقود',
        'Binance Secret Key': '✅ موجود' if BINANCE_SECRET_KEY else '❌ مفقود',
        'Telegram Token': '✅ موجود' if TELEGRAM_BOT_TOKEN else '❌ مفقود',
        'Telegram Chat ID': '✅ موجود' if TELEGRAM_CHAT_ID else '❌ مفقود'
    }
    
    for key, status in keys_status.items():
        print(f"   {key}: {status}")
    
    return all([
        BINANCE_API_KEY, 
        BINANCE_SECRET_KEY, 
        TELEGRAM_BOT_TOKEN, 
        TELEGRAM_CHAT_ID
    ])

def send_startup_message():
    """إرسال رسالة بدء التشغيل"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    
    try:
        message = f"""
<b>🚀 بوت التداول بدأ التشغيل!</b>
━━━━━━━━━━━━━━━━━━━━
<b>📅 التاريخ:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
<b>⚙️ الخادم:</b> Render.com
━━━━━━━━━━━━━━━━━━━━
<b>🔑 المفاتيح المثبتة:</b>
• Binance API: {'✅' if BINANCE_API_KEY else '❌'}
• Binance Secret: {'✅' if BINANCE_SECRET_KEY else '❌'}
• Telegram Bot: {'✅' if TELEGRAM_BOT_TOKEN else '❌'}
━━━━━━━━━━━━━━━━━━━━
<b>📊 الأزواج المتابعة:</b>
{chr(10).join([f'• {name} ({symbol})' for name, symbol in TRADING_PAIRS.items()])}
━━━━━━━━━━━━━━━━━━━━
<b>⏰ فترات المراقبة:</b>
{chr(10).join([f'• كل {interval} ثانية' for interval in TIME_INTERVALS])}
━━━━━━━━━━━━━━━━━━━━
<i>🔔 البوت يعمل ويبدأ المراقبة...</i>
"""
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, json=data, timeout=10)
        return response.status_code == 200
        
    except Exception:
        return False

# ================== الدالة الرئيسية ==================
def main():
    """الدالة الرئيسية لتشغيل البوت"""
    print("=" * 50)
    print("🚀 بدأ تشغيل بوت إشارات التداول المتكامل")
    print("=" * 50)
    
    # فحص المفاتيح
    if not check_api_keys():
        print("❌ بعض المفاتيح مفقودة! تأكد من إضافتها في Render")
        return
    
    print("✅ جميع المفاتيح موجودة في متغيرات Render")
    
    # إرسال رسالة بدء التشغيل
    if send_startup_message():
        print("✅ تم إرسال رسالة البدء إلى Telegram")
    else:
        print("⚠️ لم يتم إرسال رسالة البدء")
    
    print(f"\n📊 جاري مراقبة {len(TRADING_PAIRS)} أزواج...")
    print(f"⏱️ فترات المراقبة: {TIME_INTERVALS} ثانية")
    
    # تهيئة وقت الإرسال الأخير
    last_sent = {
        pair: {interval: 0 for interval in TIME_INTERVALS}
        for pair in TRADING_PAIRS.keys()
    }
    
    # الحلقة الرئيسية
    try:
        while True:
            current_time = time.time()
            
            for pair_name, symbol in TRADING_PAIRS.items():
                try:
                    # جلب البيانات من Binance
                    ticker_data = get_binance_ticker(symbol)
                    
                    if ticker_data:
                        # تحليل حركة السعر
                        price_signals = analyze_price_action(ticker_data)
                        
                        # جلب وتحليل الشموع إذا كانت هناك إشارات أولية
                        if price_signals:
                            klines_data = get_binance_klines(symbol, '1m', 20)
                            candle_signals = analyze_candle_pattern(klines_data)
                            
                            # دمج الإشارات
                            all_signals = price_signals + candle_signals
                        else:
                            all_signals = []
                        
                        # إرسال التنبيهات حسب الفترات الزمنية
                        for interval in TIME_INTERVALS:
                            if current_time - last_sent[pair_name][interval] >= interval:
                                if all_signals or interval == 60:  # أرسل كل 60 ثانية حتى بدون إشارات
                                    send_telegram_alert(
                                        pair_name=pair_name,
                                        interval=interval,
                                        signals=all_signals,
                                        price_data=ticker_data
                                    )
                                    last_sent[pair_name][interval] = current_time
                                    time.sleep(1)  # تأخير بسيط
                    
                    time.sleep(0.5)  # تأخير بين الأزواج
                    
                except Exception as e:
                    print(f"❌ خطأ في معالجة {pair_name}: {e}")
                    continue
            
            # انتظار قصير قبل التكرار التالي
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n🛑 إيقاف البوت...")
        
        # إرسال رسالة توقف
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            stop_msg = "<b>🛑 تم إيقاف بوت التداول</b>"
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            data = {
                'chat_id': TELEGRAM_CHAT_ID,
                'text': stop_msg,
                'parse_mode': 'HTML'
            }
            requests.post(url, json=data, timeout=5)
        
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {e}")

# ================== نقطة الدخول ==================
if __name__ == "__main__":
    main()
