# 📊 Binance Trading Signal Bot

بوت بسيط لمراقبة أسواق Binance وإرسال إشارات عبر Telegram.

## ⚙️ المتطلبات الأساسية

1. **Binance API Key** (Read Only)
2. **Telegram Bot Token** من @BotFather
3. **Telegram Chat ID** من @userinfobot

## 🚀 النشر على Render

1. انسخ جميع الملفات إلى GitHub
2. اذهب إلى [render.com](https://render.com)
3. اختر "New +" → "Web Service"
4. صل مع مستودع GitHub
5. الإعدادات:
   - **Name:** binance-signal-bot
   - **Environment:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
   - **Plan:** Free

6. أضف متغيرات البيئة:
   - `BINANCE_API_KEY`
   - `BINANCE_SECRET_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`

## 🔧 التخصيص

في `config.py` يمكنك:
- تغيير الأزواج
- تعديل الفترات الزمنية
- ضبط عتبات الإشارات

## ⚠️ ملاحظات

- البوت يعمل على الخطة المجانية
- يرسل تقارير كل دقيقة
- للتجربة والتعلم فقط
