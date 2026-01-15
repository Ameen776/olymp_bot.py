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
        this.signalSearchActive = false; // حالة البحث عن الإشارة
        this.activeSignalSearch = null; // حالة البحث النشط
        
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
/signal - طلب إشارة مع خيارات زمنية
/signal\_15 - إشارة خلال 15 ثانية
/signal\_30 - إشارة خلال 30 ثانية
/signal\_45 - إشارة خلال 45 ثانية
/signal\_60 - إشارة خلال 60 ثانية
/pause - إيقاف المراقبة
/resume - استئناف المراقبة
/signals on|off - التحكم بالإشارات

🎯 **الزوج النشط:** ${this.activePair}
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
🔍 بحث إشارة: ${this.signalSearchActive ? '🔎 جاري البحث' : '✅ جاهز'}
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
        
        // /signal - عرض خيارات الإشارات
        this.bot.onText(/\/signal$/, (msg) => {
            if (msg.from.id !== this.adminId) return;
            
            if (!this.signalsEnabled) {
                this.bot.sendMessage(msg.chat.id, '⛔ الإشارات معطلة. استخدم /signals on');
                return;
            }
            
            if (this.signalSearchActive) {
                this.bot.sendMessage(msg.chat.id, '⏳ هناك بحث عن إشارة قيد التنفيذ حالياً. يرجى الانتظار.');
                return;
            }
            
            const options = {
                reply_markup: {
                    inline_keyboard: [
                        [
                            { text: '⏱ 15 ثانية', callback_data: 'signal_15' },
                            { text: '⏱ 30 ثانية', callback_data: 'signal_30' }
                        ],
                        [
                            { text: '⏱ 45 ثانية', callback_data: 'signal_45' },
                            { text: '⏱ 60 ثانية', callback_data: 'signal_60' }
                        ],
                        [
                            { text: '🎯 الزوج النشط', callback_data: 'signal_active' },
                            { text: '❌ إلغاء', callback_data: 'signal_cancel' }
                        ]
                    ]
                },
                parse_mode: 'Markdown'
            };
            
            const message = `
📡 **طلب إشارة تداول**

اختر المدة الزمنية للبحث عن إشارة:

• **15 ثانية** - أسرع إشارة
• **30 ثانية** - إشارة متوسطة
• **45 ثانية** - إشارة جيدة
• **60 ثانية** - أفضل إشارة

🎯 **الزوج النشط:** ${this.activePair}
            `;
            
            this.bot.sendMessage(msg.chat.id, message, options);
        });
        
        // /signal_15 - إشارة خلال 15 ثانية
        this.bot.onText(/\/signal_15/, async (msg) => {
            if (msg.from.id !== this.adminId) return;
            await this.startSignalSearch(15, this.activePair, msg.chat.id);
        });
        
        // /signal_30 - إشارة خلال 30 ثانية
        this.bot.onText(/\/signal_30/, async (msg) => {
            if (msg.from.id !== this.adminId) return;
            await this.startSignalSearch(30, this.activePair, msg.chat.id);
        });
        
        // /signal_45 - إشارة خلال 45 ثانية
        this.bot.onText(/\/signal_45/, async (msg) => {
            if (msg.from.id !== this.adminId) return;
            await this.startSignalSearch(45, this.activePair, msg.chat.id);
        });
        
        // /signal_60 - إشارة خلال 60 ثانية
        this.bot.onText(/\/signal_60/, async (msg) => {
            if (msg.from.id !== this.adminId) return;
            await this.startSignalSearch(60, this.activePair, msg.chat.id);
        });
        
        // معالجة Callback Queries (للأزرار)
        this.bot.on('callback_query', async (callbackQuery) => {
            const msg = callbackQuery.message;
            const data = callbackQuery.data;
            
            if (callbackQuery.from.id !== this.adminId) {
                this.bot.answerCallbackQuery(callbackQuery.id, { text: '⛔ ليس لديك صلاحية الوصول.' });
                return;
            }
            
            if (data.startsWith('signal_')) {
                await this.handleSignalCallback(data, msg.chat.id, callbackQuery.id);
            }
            
            this.bot.answerCallbackQuery(callbackQuery.id);
        });
        
        // /pause
        this.bot.onText(/\/pause/, (msg) => {
            if (msg.from.id !== this.adminId) return;
            
            // إلغاء أي بحث عن إشارة نشط
            if (this.activeSignalSearch) {
                clearTimeout(this.activeSignalSearch.timeout);
                this.activeSignalSearch = null;
            }
            this.signalSearchActive = false;
            
            this.isPaused = true;
            this.bot.sendMessage(msg.chat.id, '⏸ تم إيقاف المراقبة مؤقتاً');
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
    
    async handleSignalCallback(callbackData, chatId, callbackId) {
        if (callbackData === 'signal_cancel') {
            if (this.activeSignalSearch) {
                clearTimeout(this.activeSignalSearch.timeout);
                this.activeSignalSearch = null;
            }
            this.signalSearchActive = false;
            this.bot.sendMessage(chatId, '❌ تم إلغاء طلب الإشارة');
            return;
        }
        
        if (callbackData === 'signal_active') {
            // عرض معلومات الزوج النشط
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
            this.bot.sendMessage(chatId, activeMsg, { parse_mode: 'Markdown' });
            return;
        }
        
        // استخراج الوقت من callback_data
        let timeSeconds = 30; // افتراضي
        if (callbackData === 'signal_15') timeSeconds = 15;
        else if (callbackData === 'signal_30') timeSeconds = 30;
        else if (callbackData === 'signal_45') timeSeconds = 45;
        else if (callbackData === 'signal_60') timeSeconds = 60;
        
        // بدء البحث عن إشارة
        await this.startSignalSearch(timeSeconds, this.activePair, chatId);
    }
    
    async startSignalSearch(durationSeconds, pair, chatId) {
        if (this.signalSearchActive) {
            this.bot.sendMessage(chatId, '⏳ هناك بحث عن إشارة قيد التنفيذ حالياً. يرجى الانتظار.');
            return;
        }
        
        if (!this.signalsEnabled) {
            this.bot.sendMessage(chatId, '⛔ الإشارات معطلة. استخدم /signals on');
            return;
        }
        
        this.signalSearchActive = true;
        
        // إرسال رسالة بدء البحث
        const searchMsg = await this.bot.sendMessage(
            chatId, 
            `🔍 **جاري البحث عن إشارة خلال ${durationSeconds} ثانية**\n\n` +
            `🎯 الزوج: ${pair}\n` +
            `⏱ الإطار: ${this.timeframe}\n` +
            `⏳ الوقت المتبقي: ${durationSeconds} ثانية`,
            { parse_mode: 'Markdown' }
        );
        
        // البحث عن أفضل إشارة خلال الفترة الزمنية
        const bestSignal = await this.searchForBestSignal(pair, durationSeconds, chatId, searchMsg.message_id);
        
        // تحديث حالة البحث
        this.signalSearchActive = false;
        
        // إرسال نتيجة البحث
        if (bestSignal) {
            const signalMsg = formatSignalMessage({
                pair: pair,
                signal: bestSignal.signal,
                confidence: bestSignal.confidence,
                analysis: bestSignal,
                duration: durationSeconds,
                auto: false
            });
            
            this.bot.sendMessage(chatId, signalMsg, { parse_mode: 'Markdown' });
        } else {
            this.bot.sendMessage(
                chatId, 
                `⏳ **لم أجد إشارة مناسبة خلال ${durationSeconds} ثانية**\n\n` +
                `🎯 الزوج: ${pair}\n` +
                `⚠️ حاول مرة أخرى أو اختر وقتاً أطول`,
                { parse_mode: 'Markdown' }
            );
        }
    }
    
    async searchForBestSignal(pair, durationSeconds, chatId, messageId) {
        const startTime = Date.now();
        const endTime = startTime + (durationSeconds * 1000);
        let bestSignal = null;
        let bestConfidence = 0;
        let checkCount = 0;
        
        // إعداد رسالة التحديث
        const updateMessage = async (remaining) => {
            const progress = Math.round(((durationSeconds - remaining) / durationSeconds) * 100);
            const progressBar = this.createProgressBar(progress);
            
            try {
                await this.bot.editMessageText(
                    `🔍 **جاري البحث عن إشارة خلال ${durationSeconds} ثانية**\n\n` +
                    `🎯 الزوج: ${pair}\n` +
                    `⏱ الإطار: ${this.timeframe}\n` +
                    `🔄 التعداد: ${checkCount}\n` +
                    `✅ أفضل ثقة: ${bestConfidence}%\n` +
                    `${progressBar} ${progress}%\n` +
                    `⏳ الوقت المتبقي: ${remaining} ثانية`,
                    {
                        chat_id: chatId,
                        message_id: messageId,
                        parse_mode: 'Markdown'
                    }
                );
            } catch (error) {
                // تجاهل أخطاء تحديث الرسالة
            }
        };
        
        // حلقة البحث عن الإشارة
        while (Date.now() < endTime && this.signalSearchActive) {
            try {
                checkCount++;
                const remaining = Math.ceil((endTime - Date.now()) / 1000);
                
                // تحديث الرسالة كل 3 ثواني
                if (checkCount % 3 === 1) {
                    await updateMessage(remaining);
                }
                
                // تحليل الزوج
                const analysis = await this.analyzePair(pair);
                
                // التحقق من الإشارة
                if (analysis && analysis.signal && analysis.signal !== 'NO_TRADE') {
                    const confidence = analysis.confidence || 0;
                    
                    // إذا كانت الثقة عالية (> 75%) نعتبرها إشارة جيدة
                    if (confidence > 75) {
                        // إذا كانت هذه أفضل إشارة حتى الآن
                        if (confidence > bestConfidence) {
                            bestConfidence = confidence;
                            bestSignal = analysis;
                            
                            // إذا كانت الثقة عالية جداً (> 85%) نعود بها فوراً
                            if (confidence > 85) {
                                console.log(`✅ وجدت إشارة قوية (${confidence}%) خلال ${checkCount} محاولات`);
                                return bestSignal;
                            }
                        }
                    }
                }
                
                // حساب الوقت المتبقي
                const timeLeft = endTime - Date.now();
                
                // إذا كان الوقت المتبقي أقل من 2 ثانية، خروج
                if (timeLeft < 2000) break;
                
                // تحديد فاصل التحقق التالي (أسرع في البداية، أبطأ مع الوقت)
                const baseInterval = 2000; // 2 ثانية
                const randomJitter = Math.random() * 1000; // تذبذب عشوائي
                const nextCheck = Math.min(baseInterval + randomJitter, timeLeft - 1000);
                
                await this.sleep(nextCheck);
                
            } catch (error) {
                console.error(`خطأ في البحث عن إشارة لـ ${pair}:`, error);
                await this.sleep(2000);
            }
        }
        
        console.log(`🔍 اكتمل البحث عن إشارة لـ ${pair}: ${checkCount} محاولة، أفضل ثقة: ${bestConfidence}%`);
        
        // إذا وجدنا إشارة (حتى لو بثقة متوسطة)
        if (bestSignal && bestConfidence > 65) {
            return bestSignal;
        }
        
        // محاولة أخيرة قبل انتهاء الوقت
        try {
            const finalAnalysis = await this.analyzePair(pair);
            if (finalAnalysis && finalAnalysis.signal && finalAnalysis.signal !== 'NO_TRADE') {
                const confidence = finalAnalysis.confidence || 0;
                if (confidence > 65) {
                    console.log(`✅ وجدت إشارة في المحاولة الأخيرة (${confidence}%)`);
                    return finalAnalysis;
                }
            }
        } catch (error) {
            console.error('خطأ في المحاولة الأخيرة:', error);
        }
        
        return null;
    }
    
    createProgressBar(percentage) {
        const filledBlocks = Math.round(percentage / 10);
        const emptyBlocks = 10 - filledBlocks;
        const filled = '█'.repeat(filledBlocks);
        const empty = '░'.repeat(emptyBlocks);
        return `[${filled}${empty}]`;
    }
    
    async analyzePair(pair) {
        try {
            // جلب بيانات السوق
            const marketData = await this.marketFetcher.fetchPairData(pair, this.timeframe);
            
            if (!marketData) {
                return { error: 'لا توجد بيانات', signal: 'NO_TRADE', confidence: 0 };
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
            return { 
                error: error.message, 
                signal: 'NO_TRADE', 
                confidence: 0,
                trend: 'N/A',
                momentum: 'N/A',
                volatility: 'N/A'
            };
        }
    }
    
    async startBackgroundMonitoring() {
        console.log('🔄 بدء مراقبة الخلفية...');
        
        const monitor = async () => {
            if (!this.isMonitoring || this.isPaused || this.signalSearchActive) {
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
                        
                        // يمكن إضافة إرسال الإشارة هنا للأدمن
                        if (this.isMonitoring) {
                            const signalMsg = formatSignalMessage({
                                pair: this.activePair,
                                signal: analysis.signal,
                                confidence: analysis.confidence,
                                analysis: analysis,
                                auto: true
                            });
                            
                            // في الوضع الحقيقي، يمكن إرسالها للأدمن
                            // this.bot.sendMessage(this.adminId, signalMsg, { parse_mode: 'Markdown' });
                        }
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
        if (trend.includes('strong') || trend.includes('قوي')) {
            score += 20;
        }
        
        // نقاط الزخم
        const momentum = (analysis.momentum || '').toLowerCase();
        if (momentum.includes('high') || momentum.includes('مرتفع') || momentum.includes('قوي')) {
            score += 15;
        }
        
        // نقاط الإشارة (إذا كانت BUY أو SELL)
        if (analysis.signal === 'BUY' || analysis.signal === 'SELL') {
            score += 25;
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

process.on('unhandledRejection', (error) => {
    console.error('❌ خطأ غير معالج:', error);
});

process.on('uncaughtException', (error) => {
    console.error('❌ استثناء غير معالج:', error);
});
