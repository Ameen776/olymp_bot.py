class SignalLogic {
    constructor() {
        this.minConfidence = 60;
    }
    
    generateSignal({ marketData, aiAnalysis, pair, timeframe }) {
        try {
            const indicators = marketData.indicators || {};
            
            // إذا كان هناك خطأ في تحليل AI
            if (aiAnalysis.error) {
                return this.createNoTradeSignal(pair, `خطأ في تحليل AI: ${aiAnalysis.error}`, 0);
            }
            
            const aiSignal = aiAnalysis.signal || 'NO_TRADE';
            const aiConfidence = aiAnalysis.confidence || 0;
            
            // التحقق من مستوى الثقة
            if (aiConfidence < this.minConfidence) {
                return this.createNoTradeSignal(
                    pair,
                    `ثقة منخفضة (${aiConfidence}% < ${this.minConfidence}%)`,
                    aiConfidence
                );
            }
            
            // تطبيق قواعد التحقق
            if (!this.validateSignal(aiSignal, indicators, aiConfidence)) {
                return this.createNoTradeSignal(
                    pair,
                    "فشل التحقق من القواعد",
                    aiConfidence
                );
            }
            
            // إنشاء إشارة
            return {
                pair: pair,
                timeframe: timeframe,
                signal: aiSignal,
                confidence: aiConfidence,
                trend: indicators.trend || 'N/A',
                momentum: aiAnalysis.momentum || 'N/A',
                volatility: indicators.volatility_level || 'N/A',
                price: marketData.currentPrice || 0,
                reason: aiAnalysis.reason || '',
                timestamp: marketData.timestamp,
                indicators: indicators
            };
            
        } catch (error) {
            console.error('خطأ في توليد الإشارة:', error);
            return this.createNoTradeSignal(pair, `خطأ تقني: ${error.message}`, 0);
        }
    }
    
    validateSignal(signal, indicators, confidence) {
        if (signal === 'NO_TRADE') return false;
        if (confidence < this.minConfidence) return false;
        
        // تحقق من التذبذب العالي
        const volatility = indicators.volatility_level || 'LOW';
        if (volatility === 'HIGH' && confidence < 80) return false;
        
        // تحقق من تناقض الاتجاه مع الإشارة
        const trend = indicators.trend || '';
        if ((signal === 'BUY' && trend === 'DOWN' && confidence < 70) ||
            (signal === 'SELL' && trend === 'UP' && confidence < 70)) {
            return false;
        }
        
        return true;
    }
    
    createNoTradeSignal(pair, reason, confidence) {
        return {
            pair: pair,
            signal: 'NO_TRADE',
            confidence: confidence,
            reason: reason,
            timestamp: new Date().toISOString()
        };
    }
}

module.exports = SignalLogic;
