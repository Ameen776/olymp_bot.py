require('dotenv').config();
const TelegramBot = require('node-telegram-bot-api');
const MarketFetcher = require('./market');
const AIAnalyzer = require('./ai-analyzer');
const SignalLogic = require('./signal-logic');
const { formatSignalMessage, validateEnvVars } = require('./utils');

// التحقق من المتغيرات البيئية
validateEnvVars();

class TradingSignalBot {
    constructor() {
        // تحميل الإعدادات
        this.botToken = process.env.TELEGRAM_BOT_TOKEN;
        this.adminId = parseInt(process.env.TELEGRAM_ADMIN_ID);
        
        // إعدادات الأزواج
        this.pairs = {
            PAIR_1: process.env.PAIR_1 || 'BTC/USDT',
            PAIR_2: process.env.PAIR_2 || 'ETH/USDT',
            PAIR_3: process.env.PAIR_3 || 'SOL/USDT'
        };
        this.activePair = process.env.ACTIVE_PAIR || this.pairs.PAIR_1;
        
        // إعدادات التحليل
        this.timeframe = process.env.TIMEFRAME || '5m';
        this.tradeDuration = parseInt(process.env.TRADE_DURATION) || 60;
        this.monitorInterval = parseInt(process.env.MONITOR_INTERVAL) || 10;
        this.signalMode = process.env.SIGNAL_MODE || 'MANUAL';
        
        // حالة البوت
        this.isMonitoring = false;
        this.isPaused = false;
        this.signalsEnabled = this.signalMode !== 'OFF';
        
        // تهيئة البوت
        this.bot = new TelegramBot(this.botToken, { polling: true });
        this.marketFetcher = new MarketFetcher();
        this.aiAnalyzer = new AIAnalyzer();
        this.signalLogic = new SignalLogic();
        
        // إعداد معالجات الأوامر
        this.setupCommandHandlers();
        
        console.log('🤖 بوت إشارات التداول جاهز للتشغيل...');
    }
    
    setupCommandHandlers() {
        // /start
        this.bot.onText(/\/start/, async (msg) => {
            if (msg.from.id !== this.adminId) {
                this.bot.sendMessage(msg.chat.id, '⛔ ليس لديك صلاحية الوصول.');
                return;
            }
            
            this.isMonitoring = true;
            this.isPaused = false;
            
            const welcomeMsg = `
🤖 **مرحبًا بك في بوت إشارات التداول الذكي**

✅ البوت قيد التشغيل
📊 وضع المراقبة: **نشط**
🔍 وضع الإشارات: **${this.signalMode}**

**الأوامر المتاحة:**
/status - حالة البوت
/pairs - عرض الأزواج
/active - الزوج النشط
/analyze - تحليل فوري
/signal - طلب إشارة
/pause - إيقاف المراقبة
/resume - استئناف المراقبة
/signals on|off - التحكم بالإشارات
            `;
            
            this.bot.sendMessage(msg.chat.id, welcomeMsg, { parse_mode: 'Markdown' });
            
            // بدء المراقبة
            this.startBackgroundMonitoring();
        });
        
        // /status
        this.bot.onText(/\/status/, (msg) => {
            if (msg.from.id !== this.adminId) return;
            
            const statusMsg = `
📊 **حالة البوت**

🔄 المراقبة: ${this.isMonitoring ? '✅ نشط' : '⏸ متوقف'}
⏸ الإيقاف المؤقت: ${this.isPaused ? '✅ نعم' : '❌ لا'}
🔔 الإشارات: ${this.signalsEnabled ? '✅ مفعل' : '❌ معطل'}
🎯 الزوج النشط: ${this.activePair}
⏱ الإطار الزمني: ${this.timeframe}
🕒 مدة الصفقة: ${this.tradeDuration} ثانية
🔄 فاصل المراقبة: ${this.monitorInterval} ثانية
📱 وضع الإشارات: ${this.signalMode}
            `;
            
            this.bot.sendMessage(msg.chat.id, statusMsg, { parse_mode: 'Markdown' });
        });
        
        // /pairs
        this.bot.onText(/\/pairs/, (msg) => {
            if (msg.from.id !== this.adminId) return;
            
            let pairsList = '';
            Object.entries(this.pairs).forEach(([key, value]) => {
                pairsList += `${key}: ${value}\n`;
            });
            
            const message = `
📈 **الأزواج المدرجة:**

${pairsList}

🎯 **الزوج النشط:** ${this.activePair}
            `;
            
            this.bot.sendMessage(msg.chat.id, message, { parse_mode: 'Markdown' });
        });
        
        // /active
        this.bot.onText(/\/active/, async (msg) => {
            if (msg.from.id !== this.adminId) return;
            
            this.bot.sendMessage(msg.chat.id, '🔍 جاري تحليل الزوج النشط...');
            
            const analysis = await this.analyzePair(this.activePair);
            
            const activeMsg = `
🎯 **الزوج النشط:** ${this.activePair}

📊 **التحليل الحالي:**
- الاتجاه: ${analysis.trend || 'N/A'}
- الزخم: ${analysis.momentum || 'N/A'}
- التذبذب: ${analysis.volatility || 'N/A'}
- الإشارة: ${analysis.signal || 'NO_TRADE'}
- الثقة: ${analysis.confidence || 0}%
            `;
            
            this.bot.sendMessage(msg.chat.id, activeMsg, { parse_mode: 'Markdown' });
        });
        
        // /analyze
        this.bot.onText(/\/analyze/, async (msg) => {
            if (msg.from.id !== this.adminId) return;
            
            this.bot.sendMessage(msg.chat.id, '🔍 جاري تحليل جميع الأزواج...');
            
            let report = '📊 **تقرير التحليل الفوري**\n\n';
            
            for (const pair of Object.values(this.pairs)) {
                const analysis = await this.analyzePair(pair);
                
                const signalEmoji = analysis.signal === 'BUY' ? '🟢' : 
                                  analysis.signal === 'SELL' ? '🔴' : '🟡';
                
                report += `${signalEmoji} **${pair}**\n`;
                report += `   الإشارة: ${analysis.signal || 'NO_TRADE'}\n`;
                report += `   الثقة: ${analysis.confidence || 0}%\n`;
                report += `   الاتجاه: ${analysis.trend || 'N/A'}\n\n`;
                
                // تأخير بين الطلبات
                await this.sleep(1000);
            }
            
            this.bot.sendMessage(msg.chat.id, report, { parse_mode: 'Markdown' });
        });
        
        // /signal
        this.bot.onText(/\/signal/, async (msg) => {
            if (msg.from.id !== this.adminId) return;
            
            if (!this.signalsEnabled) {
                this.bot.sendMessage(msg.chat.id, '⛔ الإشارات معطلة. استخدم /signals on');
                return;
            }
            
            this.bot.sendMessage(msg.chat.id, '📡 جاري طلب إشارة...');
            
            const analysis = await this.analyzePair(this.activePair);
            
            if (analysis.confidence < 60) {
                this.bot.sendMessage(msg.chat.id, '⚠️ الثقة منخفضة جدًا للإشارة (أقل من 60%)');
                return;
            }
            
            const signalMsg = formatSignalMessage({
                pair: this.activePair,
                signal: analysis.signal,
                confidence: analysis.confidence,
                analysis: analysis,
                auto: false
            });
            
            this.bot.sendMessage(msg.chat.id, signalMsg, { parse_mode: 'Markdown' });
        });
        
        // /pause
        this.bot.onText(/\/pause/, (msg) => {
            if (msg.from.id !== this.adminId) return;
            
            this.isPaused = true;
            this.bot.sendMessage(msg.chat.id, '⏸ تم إيقاف المراقبة مؤقتًا');
        });
        
        // /resume
        this.bot.onText(/\/resume/, (msg) => {
            if (msg.from.id !== this.adminId) return;
            
            this.isPaused = false;
            this.bot.sendMessage(msg.chat.id, '▶️ تم استئناف المراقبة');
        });
        
        // /signals
        this.bot.onText(/\/signals(\s+(on|off))?/, (msg, match) => {
            if (msg.from.id !== this.adminId) return;
            
            if (!match[1]) {
                this.bot.sendMessage(msg.chat.id, `🔔 وضع الإشارات الحالي: ${this.signalMode}`);
                return;
            }
            
            const mode = match[2].toUpperCase();
            this.signalsEnabled = (mode === 'ON');
            this.bot.sendMessage(msg.chat.id, `✅ تم ${mode === 'ON' ? 'تفعيل' : 'تعطيل'} الإشارات`);
        });
    }
    
    async analyzePair(pair) {
        try {
            // جلب بيانات السوق
            const marketData = await this.marketFetcher.fetchPairData(pair, this.timeframe);
            
            if (!marketData) {
                return { error: 'لا توجد بيانات' };
            }
            
            // تحليل الذكاء الاصطناعي
            const aiAnalysis = await this.aiAnalyzer.analyze(marketData);
            
            // توليد الإشارة
            const signalData = this.signalLogic.generateSignal({
                marketData: marketData,
                aiAnalysis: aiAnalysis,
                pair: pair,
                timeframe: this.timeframe
            });
            
            return signalData;
            
        } catch (error) {
            console.error(`خطأ في تحليل الزوج ${pair}:`, error);
            return { error: error.message };
        }
    }
    
    async startBackgroundMonitoring() {
        console.log('🔄 بدء مراقبة الخلفية...');
        
        const monitor = async () => {
            if (!this.isMonitoring || this.isPaused) {
                setTimeout(monitor, 5000);
                return;
            }
            
            try {
                // تحليل الأزواج الثلاثة
                let bestPair = null;
                let bestScore = -1;
                
                for (const pair of Object.values(this.pairs)) {
                    const analysis = await this.analyzePair(pair);
                    
                    // حساب نقاط الزوج
                    const score = this.calculatePairScore(analysis);
                    
                    if (score > bestScore) {
                        bestScore = score;
                        bestPair = pair;
                    }
                    
                    // تأخير بين الأزواج
                    await this.sleep(2000);
                }
                
                // تحديث الزوج النشط إذا تغير
                if (bestPair && bestPair !== this.activePair) {
                    console.log(`🔄 تغيير الزوج النشط من ${this.activePair} إلى ${bestPair}`);
                    this.activePair = bestPair;
                }
                
                // التحقق من الإشارات التلقائية
                if (this.signalMode === 'AUTO' && this.signalsEnabled && !this.isPaused) {
                    const analysis = await this.analyzePair(this.activePair);
                    
                    if (analysis.confidence > 75 && analysis.signal !== 'NO_TRADE') {
                        console.log(`📡 إشارة تلقائية: ${analysis.signal} على ${this.activePair}`);
                        // يمكن إضافة إرسال الإشارة هنا
                    }
                }
                
            } catch (error) {
                console.error('خطأ في مراقبة الخلفية:', error);
            }
            
            setTimeout(monitor, this.monitorInterval * 1000);
        };
        
        monitor();
    }
    
    calculatePairScore(analysis) {
        let score = 0;
        
        // نقاط الثقة
        const confidence = analysis.confidence || 0;
        score += confidence * 0.5;
        
        // نقاط الاتجاه القوي
        const trend = (analysis.trend || '').toLowerCase();
        if (trend.includes('strong')) {
            score += 20;
        }
        
        // نقاط الزخم
        const momentum = (analysis.momentum || '').toLowerCase();
        if (momentum.includes('high') || momentum.includes('increasing')) {
            score += 15;
        }
        
        return score;
    }
    
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// تشغيل البوت
const bot = new TradingSignalBot();

// معالجة إيقاف البرنامج
process.on('SIGINT', () => {
    console.log('\n🛑 إيقاف البوت...');
    process.exit(0);
});
