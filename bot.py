import os
import logging
import asyncio
import json
from datetime import datetime
from typing import Dict, Optional
from dotenv import load_dotenv

# تحميل المتغيرات البيئية
load_dotenv()

import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# استيراد الوحدات الداخلية
from market_data import MarketDataFetcher
from ai_analyzer import AIAnalyzer
from signal_logic import SignalLogic
from utils import format_signal_message

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TradingSignalBot:
    def __init__(self):
        # تحميل الإعدادات من متغيرات البيئة
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.admin_id = int(os.getenv('TELEGRAM_ADMIN_ID'))
        
        # إعدادات الأزواج
        self.pairs = {
            'PAIR_1': os.getenv('PAIR_1', 'BTC/USDT'),
            'PAIR_2': os.getenv('PAIR_2', 'ETH/USDT'),
            'PAIR_3': os.getenv('PAIR_3', 'SOL/USDT')
        }
        self.active_pair = os.getenv('ACTIVE_PAIR', self.pairs['PAIR_1'])
        
        # إعدادات التحليل
        self.timeframe = os.getenv('TIMEFRAME', '5m')
        self.trade_duration = int(os.getenv('TRADE_DURATION', '60'))
        self.monitor_interval = int(os.getenv('MONITOR_INTERVAL', '10'))
        self.signal_mode = os.getenv('SIGNAL_MODE', 'MANUAL')
        
        # حالة البوت
        self.is_monitoring = False
        self.is_paused = False
        self.signals_enabled = True if self.signal_mode != 'OFF' else False
        
        # تهيئة الوحدات
        self.market_fetcher = MarketDataFetcher()
        self.ai_analyzer = AIAnalyzer()
        self.signal_logic = SignalLogic()
        
        # التطبيق
        self.application = None
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة أمر /start"""
        if update.effective_user.id != self.admin_id:
            await update.message.reply_text("⛔ ليس لديك صلاحية الوصول.")
            return
            
        self.is_monitoring = True
        self.is_paused = False
        
        welcome_msg = """
🤖 **مرحبًا بك في بوت إشارات التداول الذكي**

✅ البوت قيد التشغيل
📊 وضع المراقبة: **نشط**
🔍 وضع الإشارات: **{}**

**الأوامر المتاحة:**
/status - حالة البوت
/pairs - عرض الأزواج
/active - الزوج النشط
/analyze - تحليل فوري
/signal - طلب إشارة
/pause - إيقاف المراقبة
/resume - استئناف المراقبة
/signals on|off - التحكم بالإشارات

        """.format(self.signal_mode)
        
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')
        
        # بدء مراقبة الخلفية
        asyncio.create_task(self.background_monitoring())
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة أمر /status"""
        if update.effective_user.id != self.admin_id:
            return
            
        status_msg = f"""
📊 **حالة البوت**

🔄 المراقبة: {'✅ نشط' if self.is_monitoring else '⏸ متوقف'}
⏸ الإيقاف المؤقت: {'✅ نعم' if self.is_paused else '❌ لا'}
🔔 الإشارات: {'✅ مفعل' if self.signals_enabled else '❌ معطل'}
🎯 الزوج النشط: {self.active_pair}
⏱ الإطار الزمني: {self.timeframe}
🕒 مدة الصفقة: {self.trade_duration} ثانية
🔄 فاصل المراقبة: {self.monitor_interval} ثانية
📱 وضع الإشارات: {self.signal_mode}
        """
        
        await update.message.reply_text(status_msg, parse_mode='Markdown')
    
    async def pairs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة أمر /pairs"""
        if update.effective_user.id != self.admin_id:
            return
            
        pairs_list = "\n".join([f"{key}: {value}" for key, value in self.pairs.items()])
        msg = f"""
📈 **الأزواج المدرجة:**

{pairs_list}

🎯 **الزوج النشط:** {self.active_pair}
        """
        
        await update.message.reply_text(msg, parse_mode='Markdown')
    
    async def active_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة أمر /active"""
        if update.effective_user.id != self.admin_id:
            return
            
        # تحليل الزوج النشط
        analysis = await self.analyze_pair(self.active_pair)
        
        msg = f"""
🎯 **الزوج النشط:** {self.active_pair}

📊 **التحليل الحالي:**
- الاتجاه: {analysis.get('trend', 'N/A')}
- الزخم: {analysis.get('momentum', 'N/A')}
- التذبذب: {analysis.get('volatility', 'N/A')}
- الإشارة: {analysis.get('signal', 'NO_TRADE')}
- الثقة: {analysis.get('confidence', 0)}%
        """
        
        await update.message.reply_text(msg, parse_mode='Markdown')
    
    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة أمر /analyze"""
        if update.effective_user.id != self.admin_id:
            return
            
        await update.message.reply_text("🔍 جاري التحليل...")
        
        # تحليل جميع الأزواج
        analyses = {}
        for pair in self.pairs.values():
            analysis = await self.analyze_pair(pair)
            analyses[pair] = analysis
            await asyncio.sleep(1)  # تأخير بين الطلبات
        
        # إنشاء تقرير
        report = "📊 **تقرير التحليل الفوري**\n\n"
        for pair, analysis in analyses.items():
            signal_emoji = "🟢" if analysis.get('signal') == 'BUY' else "🔴" if analysis.get('signal') == 'SELL' else "🟡"
            report += f"{signal_emoji} **{pair}**\n"
            report += f"   الإشارة: {analysis.get('signal', 'NO_TRADE')}\n"
            report += f"   الثقة: {analysis.get('confidence', 0)}%\n"
            report += f"   الاتجاه: {analysis.get('trend', 'N/A')}\n\n"
        
        await update.message.reply_text(report, parse_mode='Markdown')
    
    async def signal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة أمر /signal"""
        if update.effective_user.id != self.admin_id:
            return
            
        if not self.signals_enabled:
            await update.message.reply_text("⛔ الإشارات معطلة. استخدم /signals on")
            return
            
        await update.message.reply_text("📡 جاري طلب إشارة...")
        
        # تحليل الزوج النشط
        analysis = await self.analyze_pair(self.active_pair)
        
        # التحقق من مستوى الثقة
        if analysis.get('confidence', 0) < 60:  # عتبة الثقة
            await update.message.reply_text("⚠️ الثقة منخفضة جدًا للإشارة (أقل من 60%)")
            return
            
        # تنسيق وإرسال الإشارة
        signal_msg = format_signal_message(
            pair=self.active_pair,
            signal=analysis['signal'],
            confidence=analysis['confidence'],
            analysis=analysis
        )
        
        await update.message.reply_text(signal_msg, parse_mode='Markdown')
    
    async def pause_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة أمر /pause"""
        if update.effective_user.id != self.admin_id:
            return
            
        self.is_paused = True
        await update.message.reply_text("⏸ تم إيقاف المراقبة مؤقتًا")
    
    async def resume_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة أمر /resume"""
        if update.effective_user.id != self.admin_id:
            return
            
        self.is_paused = False
        await update.message.reply_text("▶️ تم استئناف المراقبة")
    
    async def signals_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة أمر /signals"""
        if update.effective_user.id != self.admin_id:
            return
            
        if len(context.args) == 0:
            await update.message.reply_text(f"🔔 وضع الإشارات الحالي: {self.signal_mode}")
            return
            
        mode = context.args[0].upper()
        if mode not in ['ON', 'OFF']:
            await update.message.reply_text("استخدم: /signals on أو /signals off")
            return
            
        self.signals_enabled = (mode == 'ON')
        await update.message.reply_text(f"✅ تم {'تفعيل' if mode == 'ON' else 'تعطيل'} الإشارات")
    
    async def analyze_pair(self, pair: str) -> Dict:
        """تحليل زوج معين"""
        try:
            # جلب بيانات السوق
            market_data = await self.market_fetcher.fetch_pair_data(pair, self.timeframe)
            
            if not market_data:
                return {'error': 'لا توجد بيانات'}
            
            # تحليل الذكاء الاصطناعي
            ai_analysis = await self.ai_analyzer.analyze(market_data)
            
            # توليد الإشارة
            signal_data = self.signal_logic.generate_signal(
                market_data=market_data,
                ai_analysis=ai_analysis,
                pair=pair,
                timeframe=self.timeframe
            )
            
            return signal_data
            
        except Exception as e:
            logger.error(f"خطأ في تحليل الزوج {pair}: {e}")
            return {'error': str(e)}
    
    async def background_monitoring(self):
        """مراقبة الخلفية للأزواج"""
        while True:
            try:
                if not self.is_monitoring or self.is_paused:
                    await asyncio.sleep(5)
                    continue
                
                # تحليل الأزواج الثلاثة
                best_pair = None
                best_score = -1
                
                for pair in self.pairs.values():
                    analysis = await self.analyze_pair(pair)
                    
                    # حساب نقاط الزوج
                    score = self.calculate_pair_score(analysis)
                    
                    if score > best_score:
                        best_score = score
                        best_pair = pair
                    
                    await asyncio.sleep(2)  # تأخير بين الأزواج
                
                # تحديث الزوج النشط إذا تغير
                if best_pair and best_pair != self.active_pair:
                    old_pair = self.active_pair
                    self.active_pair = best_pair
                    logger.info(f"تم تغيير الزوج النشط من {old_pair} إلى {best_pair}")
                
                # التحقق من إرسال الإشارات التلقائية
                if (self.signal_mode == 'AUTO' and 
                    self.signals_enabled and 
                    not self.is_paused):
                    
                    analysis = await self.analyze_pair(self.active_pair)
                    
                    # شروط الإشارة التلقائية
                    if (analysis.get('confidence', 0) > 75 and 
                        analysis.get('signal') != 'NO_TRADE'):
                        
                        signal_msg = format_signal_message(
                            pair=self.active_pair,
                            signal=analysis['signal'],
                            confidence=analysis['confidence'],
                            analysis=analysis,
                            auto=True
                        )
                        
                        # إرسال الإشارة (في بيئة حقيقية، سيتم إرسالها للأدمن)
                        logger.info(f"إشارة تلقائية: {analysis['signal']} على {self.active_pair}")
                
                await asyncio.sleep(self.monitor_interval)
                
            except Exception as e:
                logger.error(f"خطأ في مراقبة الخلفية: {e}")
                await asyncio.sleep(10)
    
    def calculate_pair_score(self, analysis: Dict) -> float:
        """حساب نقاط الزوج بناءً على التحليل"""
        score = 0
        
        # نقاط الثقة
        confidence = analysis.get('confidence', 0)
        score += confidence * 0.5
        
        # نقاط الاتجاه القوي
        trend = analysis.get('trend', '').lower()
        if 'strong' in trend:
            score += 20
        
        # نقاط الزخم
        momentum = analysis.get('momentum', '').lower()
        if 'high' in momentum or 'increasing' in momentum:
            score += 15
        
        return score
    
    def run(self):
        """تشغيل البوت"""
        # إنشاء التطبيق
        self.application = Application.builder().token(self.bot_token).build()
        
        # إضافة handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("status", self.status))
        self.application.add_handler(CommandHandler("pairs", self.pairs_command))
        self.application.add_handler(CommandHandler("active", self.active_command))
        self.application.add_handler(CommandHandler("analyze", self.analyze_command))
        self.application.add_handler(CommandHandler("signal", self.signal_command))
        self.application.add_handler(CommandHandler("pause", self.pause_command))
        self.application.add_handler(CommandHandler("resume", self.resume_command))
        self.application.add_handler(CommandHandler("signals", self.signals_command))
        
        # بدء البوت
        logger.info("🚀 بدء تشغيل بوت إشارات التداول...")
        
        # استخدام polling للاستضافة على Render
        port = int(os.getenv('PORT', 10000))
        
        # بدء polling
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

def main():
    """الدالة الرئيسية"""
    bot = TradingSignalBot()
    bot.run()

if __name__ == '__main__':
    main()
