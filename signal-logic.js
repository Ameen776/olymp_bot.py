class SignalLogic {
    constructor() {
        this.minConfidence = 65; // خفضنا العتبة قليلاً للإشارات السريعة
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
            
            // إذا كانت الثقة منخفضة جداً
            if (aiConfidence < 50) {
                return this.createNoTradeSignal(
                    pair,
                    `ثقة منخفضة جداً (${aiConfidence}%)`,
                    aiConfidence
                );
            }
            
            // تحسين الإشارة بناءً على المؤشرات الفنية
            const enhancedSignal = this.enhanceWithTechnicalAnalysis(aiSignal, aiConfidence, indicators);
            
            // إنشاء إشارة
            return {
                pair: pair,
                timeframe: timeframe,
                signal: enhancedSignal.signal,
                confidence: enhancedSignal.confidence,
                trend: indicators.trend || 'N/A',
                momentum: aiAnalysis.momentum || 'N/A',
                volatility: indicators.volatility_level || 'N/A',
                price: marketData.currentPrice || 0,
                reason: enhancedSignal.reason || aiAnalysis.reason || '',
                timestamp: marketData.timestamp,
                indicators: indicators,
                ohlcData: marketData.ohlcData
            };
            
        } catch (error) {
            console.error('خطأ في توليد الإشارة:', error);
            return this.createNoTradeSignal(pair, `خطأ تقني: ${error.message}`, 0);
        }
    }
    
    enhanceWithTechnicalAnalysis(aiSignal, aiConfidence, indicators) {
        let finalSignal = aiSignal;
        let finalConfidence = aiConfidence;
        let reason = '';
        
        // تحسين بناءً على RSI
        const rsi = indicators.rsi || 50;
        if (rsi > 70 && aiSignal === 'BUY') {
            finalConfidence = Math.max(aiConfidence - 15, 40);
            reason = 'RSI يشير إلى ذروة شراء';
        } else if (rsi < 30 && aiSignal === 'SELL') {
            finalConfidence = Math.max(aiConfidence - 15, 40);
            reason = 'RSI يشير إلى ذروة بيع';
        } else if ((rsi > 50 && aiSignal === 'BUY') || (rsi < 50 && aiSignal === 'SELL')) {
            finalConfidence = aiConfidence + 5;
            reason = 'RSI يدعم الإشارة';
        }
        
        // تحسين بناءً على التذبذب
        const volatility = indicators.volatility || 0;
        if (volatility > 3 && finalConfidence > 80) {
            // تخفيض الثقة قليلاً في الأسواق المتقلبة
            finalConfidence = Math.max(finalConfidence - 5, 60);
            if (reason) reason += '، ';
            reason += 'تذبذب مرتفع';
        }
        
        // إذا كانت الثقة النهائية أقل من الحد الأدنى، نغير الإشارة إلى NO_TRADE
        if (finalConfidence < this.minConfidence) {
            finalSignal = 'NO_TRADE';
            reason = `ثقة منخفضة (${finalConfidence}% < ${this.minConfidence}%)`;
        }
        
        return {
            signal: finalSignal,
            confidence: Math.min(finalConfidence, 100),
            reason: reason
        };
    }
    
    validateSignal(signal, indicators, confidence) {
        if (signal === 'NO_TRADE') return false;
        if (confidence < this.minConfidence) return false;
        
        // تحقق من التذبذب العالي جداً
        const volatility = indicators.volatility_level || 'LOW';
        if (volatility === 'HIGH' && confidence < 75) return false;
        
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
