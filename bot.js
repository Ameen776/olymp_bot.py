const axios = require('axios');
const CryptoJS = require('crypto-js');

// ========== قراءة المفاتيح من Render ==========
const BINANCE_API_KEY = process.env.BINANCE_API_KEY || '';
const BINANCE_SECRET_KEY = process.env.BINANCE_SECRET_KEY || '';
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN || '';
const TELEGRAM_CHAT_ID = process.env.TELEGRAM_CHAT_ID || '';

// ========== المتغيرات العامة ==========
let SELECTED_PAIR = 'BTCUSDT';
let SELECTED_PAIR_NAME = 'BTCOTC';
let BOT_ACTIVE = true;
let LAST_PRICE = 0;
let LAST_SIGNAL_TIME = {};
let SIGNAL_COOLDOWN = 2000; // تبريد 2 ثانية بين الإشارات
let MONITORING_INTERVAL = 100; // 100ms مراقبة سريعة جداً

// ========== قائمة الأزواج المتاحة ==========
const AVAILABLE_PAIRS = {
    'BTCOTC': {
        name: 'Bitcoin OTC',
        symbol: 'BTCUSDT',
        volatility: 'HIGH'
    },
    'XRPOTC': {
        name: 'Ripple OTC', 
        symbol: 'XRPUSDT',
        volatility: 'MEDIUM'
    },
    'SOLOTC': {
        name: 'Solana OTC',
        symbol: 'SOLUSDT',
        volatility: 'HIGH'
    },
    'AUDCADOTC': {
        name: 'AUD/CAD OTC',
        symbol: 'AUDCAD',
        volatility: 'LOW'
    }
};

// ========== إعدادات المراقبة الحية ==========
const REAL_TIME_SETTINGS = {
    PRICE_CHANGE_THRESHOLD: 0.05, // 0.05% تغير فوري
    MIN_VOLUME: 10000,
    CHECK_INTERVAL: 100, // كل 100ms
    MAX_SIGNALS_PER_MINUTE: 30 // حد الإشارات في الدقيقة
};

// ========== دوال Telegram ==========
async function sendTelegramMessage(text, reply_markup = null) {
    if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_CHAT_ID) {
        console.log('❌ مفاتيح Telegram مفقودة');
        return false;
    }

    try {
        const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`;
        const data = {
            chat_id: TELEGRAM_CHAT_ID,
            text: text,
            parse_mode: 'HTML',
            disable_web_page_preview: true
        };

        if (reply_markup) {
            data.reply_markup = reply_markup;
        }

        const response = await axios.post(url, data, { timeout: 5000 });
        return response.status === 200;
    } catch (error) {
        console.log('❌ خطأ في إرسال Telegram:', error.message);
        return false;
    }
}

// ========== لوحة الأوامر ==========
function createCommandKeyboard() {
    return {
        keyboard: [
            [
                { text: '🚀 BTCOTC' },
                { text: '🌀 XRPOTC' }
            ],
            [
                { text: '⚡ SOLOTC' },
                { text: '💵 AUD/CAD' }
            ],
            [
                { text: '▶️ تشغيل فوري' },
                { text: '⏸️ إيقاف فوري' }
            ],
            [
                { text: '📊 حالة البوت' },
                { text: '⚙️ الإعدادات' }
            ]
        ],
        resize_keyboard: true,
        one_time_keyboard: false
    };
}

// ========== معالجة الأوامر ==========
async function handleCommand(command) {
    console.log(`📝 أمر: ${command}`);

    switch (command) {
        case '🚀 BTCOTC':
            await selectPair('BTCOTC', 'BTCUSDT', 'Bitcoin OTC');
            break;
            
        case '🌀 XRPOTC':
            await selectPair('XRPOTC', 'XRPUSDT', 'Ripple OTC');
            break;
            
        case '⚡ SOLOTC':
            await selectPair('SOLOTC', 'SOLUSDT', 'Solana OTC');
            break;
            
        case '💵 AUD/CAD':
            await selectPair('AUDCADOTC', 'AUDCAD', 'AUD/CAD OTC');
            break;
            
        case '▶️ تشغيل فوري':
            BOT_ACTIVE = true;
            await sendTelegramMessage('✅ <b>تم تشغيل المراقبة الفورية!</b>\nالبوت يراقب السوق في الوقت الحقيقي ⚡', createCommandKeyboard());
            break;
            
        case '⏸️ إيقاف فوري':
            BOT_ACTIVE = false;
            await sendTelegramMessage('⏸️ <b>تم إيقاف المراقبة الفورية</b>', createCommandKeyboard());
            break;
            
        case '📊 حالة البوت':
            await botStatus();
            break;
            
        case '⚙️ الإعدادات':
            await showSettings();
            break;
            
        default:
            await sendTelegramMessage(`❌ أمر غير معروف: ${command}`);
    }
}

// ========== اختيار الزوج ==========
async function selectPair(pairName, symbol, displayName) {
    SELECTED_PAIR = symbol;
    SELECTED_PAIR_NAME = pairName;
    LAST_PRICE = 0;
    LAST_SIGNAL_TIME = {};
    
    const message = `
✅ <b>تم اختيار الزوج بنجاح!</b>

⚡ <b>المراقبة الفورية:</b> 🔥 تشغيل
⏱️ <b>سرعة المراقبة:</b> 100ms
📊 <b>الزوج الجديد:</b> ${displayName}
💰 <b>الرمز:</b> ${symbol}

🚨 <b>نظام الإشارات:</b>
• مراقبة مستمرة 24/7
• إشارات فورية عند التغير
• بدون فواصل زمنية
• وقت حقيقي مباشر

🔔 <b>يبدأ المراقبة الآن...</b>
    `;
    
    await sendTelegramMessage(message, createCommandKeyboard());
    console.log(`✅ تم اختيار الزوج: ${pairName}`);
}

// ========== حالة البوت ==========
async function botStatus() {
    const status = BOT_ACTIVE ? '🟢 مراقبة فورية' : '🔴 متوقف';
    
    const message = `
📊 <b>حالة البوت الحية</b>
━━━━━━━━━━━━━━━━━━━━
<b>⚡ النظام:</b> مراقبة وقت حقيقي
<b>⏱️ السرعة:</b> كل 100ms
<b>📊 الزوج النشط:</b> ${SELECTED_PAIR_NAME}
<b>💰 الرمز:</b> ${SELECTED_PAIR}
<b>🔄 الحالة:</b> ${status}
<b>📈 آخر سعر:</b> ${LAST_PRICE || 'غير معروف'}
━━━━━━━━━━━━━━━━━━━━
<b>⚙️ إعدادات المراقبة:</b>
• عتبة التغير: ${REAL_TIME_SETTINGS.PRICE_CHANGE_THRESHOLD}%
• سرعة الفحص: ${REAL_TIME_SETTINGS.CHECK_INTERVAL}ms
• الحد الأقصى: ${REAL_TIME_SETTINGS.MAX_SIGNALS_PER_MINUTE} إشارة/دقيقة
━━━━━━━━━━━━━━━━━━━━
<i>استخدم الأزرار للتحكم الفوري</i>
    `;
    
    await sendTelegramMessage(message, createCommandKeyboard());
}

// ========== إعدادات البوت ==========
async function showSettings() {
    const message = `
⚙️ <b>إعدادات المراقبة الفورية</b>
━━━━━━━━━━━━━━━━━━━━
<b>⏱️ سرعة المراقبة:</b> ${MONITORING_INTERVAL}ms
<b>📈 عتبة التغير:</b> ${REAL_TIME_SETTINGS.PRICE_CHANGE_THRESHOLD}%
<b>🔄 تبريد الإشارات:</b> ${SIGNAL_COOLDOWN}ms
<b>🚨 الحد الأقصى:</b> ${REAL_TIME_SETTINGS.MAX_SIGNALS_PER_MINUTE} إشارة/دقيقة
━━━━━━━━━━━━━━━━━━━━
<b>📊 الزوج الحالي:</b> ${SELECTED_PAIR_NAME}
<b>💰 التقلبية:</b> ${AVAILABLE_PAIRS[SELECTED_PAIR_NAME].volatility}
━━━━━━━━━━━━━━━━━━━━
<i>⚡ البوت يراقب في الوقت الحقيقي بدون توقف</i>
    `;
    
    await sendTelegramMessage(message, createCommandKeyboard());
}

// ========== مراقبة Binance فورية ==========
async function monitorBinanceRealtime() {
    if (!BOT_ACTIVE) return null;
    
    try {
        // استخدام WebSocket Simulation (طلب سريع جداً)
        const priceUrl = `https://api.binance.com/api/v3/ticker/price?symbol=${SELECTED_PAIR}`;
        const tradesUrl = `https://api.binance.com/api/v3/trades?symbol=${SELECTED_PAIR}&limit=5`;
        
        const [priceResponse, tradesResponse] = await Promise.all([
            axios.get(priceUrl, { timeout: 3000 }),
            axios.get(tradesUrl, { timeout: 3000 })
        ]);
        
        if (priceResponse.data && tradesResponse.data) {
            const currentPrice = parseFloat(priceResponse.data.price);
            const recentTrades = tradesResponse.data;
            
            // تحليل الصفقات الحديثة
            let buyVolume = 0;
            let sellVolume = 0;
            let totalVolume = 0;
            
            recentTrades.forEach(trade => {
                const volume = parseFloat(trade.qty) * parseFloat(trade.price);
                totalVolume += volume;
                
                if (trade.isBuyerMaker) {
                    sellVolume += volume;
                } else {
                    buyVolume += volume;
                }
            });
            
            return {
                symbol: SELECTED_PAIR,
                price: currentPrice,
                timestamp: Date.now(),
                volume: totalVolume,
                buyVolume: buyVolume,
                sellVolume: sellVolume,
                tradeCount: recentTrades.length,
                isBullish: buyVolume > sellVolume * 1.2,
                isBearish: sellVolume > buyVolume * 1.2
            };
        }
        return null;
    } catch (error) {
        console.log(`❌ خطأ في المراقبة: ${error.message}`);
        return null;
    }
}

// ========== تحليل فوري للإشارات ==========
function analyzeRealtimeSignal(marketData) {
    if (!marketData || LAST_PRICE === 0) {
        if (marketData) LAST_PRICE = marketData.price;
        return null;
    }
    
    const currentPrice = marketData.price;
    const priceChange = ((currentPrice - LAST_PRICE) / LAST_PRICE) * 100;
    const absChange = Math.abs(priceChange);
    
    // تحقق من وقت التبريد
    const now = Date.now();
    const lastSignalTime = LAST_SIGNAL_TIME[SELECTED_PAIR_NAME] || 0;
    if (now - lastSignalTime < SIGNAL_COOLDOWN) {
        return null;
    }
    
    // فقط إذا كان التغير كبيراً بما يكفي
    if (absChange >= REAL_TIME_SETTINGS.PRICE_CHANGE_THRESHOLD) {
        const signal = {
            type: priceChange > 0 ? 'BUY' : 'SELL',
            strength: absChange > 0.1 ? 'STRONG' : 'MODERATE',
            priceChange: priceChange,
            currentPrice: currentPrice,
            previousPrice: LAST_PRICE,
            volume: marketData.volume,
            timestamp: marketData.timestamp,
            isBullish: marketData.isBullish,
            isBearish: marketData.isBearish,
            tradeCount: marketData.tradeCount
        };
        
        LAST_PRICE = currentPrice;
        LAST_SIGNAL_TIME[SELECTED_PAIR_NAME] = now;
        
        return signal;
    }
    
    LAST_PRICE = currentPrice;
    return null;
}

// ========== إنشاء إشارة فورية ==========
function createRealtimeSignalReport(signal) {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('ar-SA');
    const milliseconds = now.getMilliseconds().toString().padStart(3, '0');
    
    const emoji = signal.type === 'BUY' ? '🟢' : '🔴';
    const action = signal.type === 'BUY' ? 'شراء' : 'بيع';
    const direction = signal.type === 'BUY' ? 'صعود' : 'هبوط';
    
    let report = `
${emoji} <b>إشارة ${action} فورية!</b>
━━━━━━━━━━━━━━━━━━━━
<b>⏱️ الوقت الدقيق:</b> ${timeStr}.${milliseconds}
<b>⚡ السرعة:</b> وقت حقيقي مباشر
<b>📊 الزوج:</b> ${SELECTED_PAIR_NAME}
<b>💰 الرمز:</b> ${SELECTED_PAIR}
━━━━━━━━━━━━━━━━━━━━
<b>💵 السعر الحالي:</b> $${signal.currentPrice.toFixed(4)}
<b>📈 السعر السابق:</b> $${signal.previousPrice.toFixed(4)}
<b>🔄 التغير الفوري:</b> <code>${signal.priceChange >= 0 ? '+' : ''}${signal.priceChange.toFixed(4)}%</code>
<b>📊 الحجم:</b> $${signal.volume.toFixed(2)}
<b>🔢 عدد الصفقات:</b> ${signal.tradeCount}
<b>📈 اتجاه السوق:</b> ${signal.isBullish ? 'صعودي قوي' : signal.isBearish ? 'هبوطي قوي' : 'متوازن'}
━━━━━━━━━━━━━━━━━━━━
<b>🎯 التوصية الفورية:</b>
• <b>فتح صفقة ${action}</b> فوراً
• ${direction} سريع في السوق
• حركة قوية خلال أجزاء الثانية

<b>💰 مستويات السعر:</b>
${signal.type === 'BUY' ? 
`• السعر المستهدف: $${(signal.currentPrice * 1.005).toFixed(4)}
• وقف الخسارة: $${(signal.currentPrice * 0.998).toFixed(4)}` : 
`• السعر المستهدف: $${(signal.currentPrice * 0.995).toFixed(4)}
• وقف الخسارة: $${(signal.currentPrice * 1.002).toFixed(4)}`}
━━━━━━━━━━━━━━━━━━━━
<b>⚡ نظام المراقبة:</b>
• سرعة: 100ms
• دقة: 0.01%
• وقت: حقيقي مباشر
━━━━━━━━━━━━━━━━━━━━
<i>🚨 إشارة فورية - التحرك السريع</i>
`;
    
    return report;
}

// ========== المراقبة الفورية المستمرة ==========
async function startRealtimeMonitoring() {
    console.log('⚡ بدأ المراقبة الفورية...');
    
    let signalCount = 0;
    let lastMinuteReset = Date.now();
    
    while (true) {
        try {
            if (!BOT_ACTIVE) {
                await sleep(1000);
                continue;
            }
            
            // إعادة تعيين العداد كل دقيقة
            if (Date.now() - lastMinuteReset > 60000) {
                signalCount = 0;
                lastMinuteReset = Date.now();
            }
            
            // التحقق من الحد الأقصى للإشارات
            if (signalCount >= REAL_TIME_SETTINGS.MAX_SIGNALS_PER_MINUTE) {
                await sleep(100);
                continue;
            }
            
            // مراقبة السوق
            const marketData = await monitorBinanceRealtime();
            
            if (marketData) {
                const signal = analyzeRealtimeSignal(marketData);
                
                if (signal) {
                    const report = createRealtimeSignalReport(signal);
                    
                    if (report) {
                        await sendTelegramMessage(report, createCommandKeyboard());
                        signalCount++;
                        
                        console.log(`⚡ إشارة ${signal.type} فورية! التغير: ${signal.priceChange.toFixed(4)}%`);
                        
                        // تبريد قصير بعد الإشارة
                        await sleep(500);
                    }
                }
                
                // عرض سعر في الكونسول (اختياري)
                if (Date.now() % 5000 < 100) { // كل 5 ثواني
                    console.log(`📊 ${SELECTED_PAIR}: $${marketData.price} | B:$${marketData.buyVolume.toFixed(0)} | S:$${marketData.sellVolume.toFixed(0)}`);
                }
            }
            
            // انتظار قصير جداً للمراقبة التالية
            await sleep(MONITORING_INTERVAL);
            
        } catch (error) {
            console.log('❌ خطأ في المراقبة:', error.message);
            await sleep(1000);
        }
    }
}

// ========== دالة المساعدة للنوم ==========
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ========== بدء البوت الرئيسي ==========
async function startBot() {
    console.log('='.repeat(60));
    console.log('⚡ BINANCE REAL-TIME SIGNAL BOT');
    console.log('='.repeat(60));
    
    console.log('\n🔍 فحص المفاتيح من Render:');
    console.log('Binance API:', BINANCE_API_KEY ? '✅' : '❌');
    console.log('Binance Secret:', BINANCE_SECRET_KEY ? '✅' : '❌');
    console.log('Telegram Token:', TELEGRAM_BOT_TOKEN ? '✅' : '❌');
    console.log('Telegram Chat ID:', TELEGRAM_CHAT_ID ? '✅' : '❌');
    
    // رسالة البدء
    const welcomeMessage = `
⚡ <b>مرحباً بك في البوت الفوري!</b>

🚀 <b>مميزات النظام:</b>
• مراقبة وقت حقيقي مباشر
• سرعة 100ms بين الفحوصات
• إشارات فورية عند أي تغير
• بدون فواصل زمنية
• نظام تبريد ذكي

📊 <b>الزوج الافتراضي:</b> Bitcoin OTC (BTCUSDT)

<b>🎯 كيفية الاستخدام:</b>
1. اختر الزوج من الأزرار
2. اضغط "▶️ تشغيل فوري"  
3. استلم الإشارات فورياً

<i>⚡ جاهز للمراقبة الفورية...</i>
    `;
    
    await sendTelegramMessage(welcomeMessage, createCommandKeyboard());
    console.log('\n✅ تم إرسال رسالة الترحيب');
    
    console.log('\n⚡ بدأ المراقبة الفورية...');
    console.log('━'.repeat(40));
    
    // بدء المراقبة الفورية في خلفية
    startRealtimeMonitoring().catch(error => {
        console.error('❌ خطأ فادح في المراقبة:', error);
    });
    
    // تحديث حالة النظام
    setInterval(() => {
        const now = new Date();
        console.log(`⏰ ${now.toLocaleTimeString('ar-SA')} | الزوج: ${SELECTED_PAIR_NAME} | السعر: ${LAST_PRICE || 'جاري...'}`);
    }, 10000);
}

// ========== تشغيل البوت ==========
startBot();
