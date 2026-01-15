const OpenAI = require('openai');
const { GoogleGenerativeAI } = require('@google/generative-ai');

class AIAnalyzer {
    constructor() {
        this.provider = process.env.AI_PROVIDER || 'openai';
        
        if (this.provider === 'openai') {
            this.openai = new OpenAI({
                apiKey: process.env.OPENAI_API_KEY
            });
        } else if (this.provider === 'gemini') {
            this.genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
        }
    }
    
    async analyze(marketData) {
        try {
            const prompt = this.createAnalysisPrompt(marketData);
            
            if (this.provider === 'openai') {
                return await this.analyzeWithOpenAI(prompt, marketData);
            } else if (this.provider === 'gemini') {
                return await this.analyzeWithGemini(prompt, marketData);
            } else {
                return this.createDefaultAnalysis(marketData);
            }
            
        } catch (error) {
            console.error('خطأ في تحليل AI:', error);
            return this.createDefaultAnalysis(marketData);
        }
    }
    
    async analyzeWithOpenAI(prompt, marketData) {
        const response = await this.openai.chat.completions.create({
            model: process.env.AI_MODEL || 'gpt-3.5-turbo',
            messages: [
                {
                    role: "system",
                    content: "أنت محلل أسواق مالية خبير. قم بتحليل بيانات السوق وأعط تقييمًا موضوعيًا. استخدم فقط البيانات المقدمة."
                },
                {
                    role: "user",
                    content: prompt
                }
            ],
            temperature: 0.3,
            max_tokens: 300
        });
        
        const analysisText = response.choices[0].message.content;
        return this.parseAIResponse(analysisText, marketData);
    }
    
    async analyzeWithGemini(prompt, marketData) {
        const model = this.genAI.getGenerativeModel({ model: "gemini-pro" });
        const result = await model.generateContent(prompt);
        const response = await result.response;
        const analysisText = response.text();
        
        return this.parseAIResponse(analysisText, marketData);
    }
    
    createAnalysisPrompt(marketData) {
        const pair = marketData.pair || 'N/A';
        const price = marketData.currentPrice || 0;
        const indicators = marketData.indicators || {};
        
        return `
        تحليل زوج التداول: ${pair}
        السعر الحالي: ${price}
        
        المؤشرات الفنية:
        - الاتجاه: ${indicators.trend || 'N/A'} (قوة: ${indicators.trend_strength || 0}%)
        - RSI: ${indicators.rsi || 0}
        - الزخم: ${indicators.momentum || 0}
        - التذبذب: ${indicators.volatility || 0}% (مستوى: ${indicators.volatility_level || 'N/A'})
        
        قم بتحليل هذه البيانات وأعط:
        1. تحليل الاتجاه (صاعد/هابط/جانبي)
        2. مستوى الزخم (مرتفع/منخفض)
        3. مستوى المخاطرة (مرتفع/متوسط/منخفض)
        4. توصية مختصرة (شراء/بيع/انتظار)
        5. نسبة الثقة (0-100%)
        
        أجب بتنسيق JSON:
        {
            "trend": "صاعد/هابط/جانبي",
            "momentum": "مرتفع/متوسط/منخفض",
            "risk": "مرتفع/متوسط/منخفض",
            "signal": "BUY/SELL/NO_TRADE",
            "confidence": 0-100,
            "reason": "سبب موجز"
        }
        `;
    }
    
    parseAIResponse(responseText, marketData) {
        try {
            // البحث عن JSON في النص
            const jsonMatch = responseText.match(/\{[\s\S]*\}/);
            
            if (jsonMatch) {
                const analysis = JSON.parse(jsonMatch[0]);
                
                // التأكد من وجود القيم المطلوبة
                return {
                    trend: analysis.trend || 'جانبي',
                    momentum: analysis.momentum || 'متوسط',
                    risk: analysis.risk || 'متوسط',
                    signal: analysis.signal || 'NO_TRADE',
                    confidence: parseInt(analysis.confidence) || 50,
                    reason: analysis.reason || 'لا يوجد تحليل واضح',
                    pair: marketData.pair,
                    price: marketData.currentPrice,
                    timestamp: marketData.timestamp
                };
            }
        } catch (error) {
            console.error('خطأ في تحليل استجابة AI:', error);
        }
        
        // التحليل الافتراضي في حالة الفشل
        return this.createDefaultAnalysis(marketData);
    }
    
    createDefaultAnalysis(marketData) {
        return {
            trend: 'جانبي',
            momentum: 'متوسط',
            risk: 'متوسط',
            signal: 'NO_TRADE',
            confidence: 50,
            reason: 'لا يوجد تحليل واضح',
            pair: marketData.pair,
            price: marketData.currentPrice,
            timestamp: marketData.timestamp
        };
    }
}

module.exports = AIAnalyzer;
