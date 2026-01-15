import logging
from typing import Dict

logger = logging.getLogger(__name__)

class SignalLogic:
    def __init__(self):
        self.min_confidence = 60  # الحد الأدنى للثقة
        
    def generate_signal(self, market_data: Dict, ai_analysis: Dict, 
                       pair: str, timeframe: str) -> Dict:
        """توليد إشارة تداول"""
        try:
            # استخراج البيانات
            indicators = market_data.get('indicators', {})
            
            # التأكد من وجود تحليل AI
            if 'error' in ai_analysis:
                return self.create_no_trade_signal(
                    pair=pair,
                    reason=f"خطأ في تحليل AI: {ai_analysis['error']}",
                    confidence=0
                )
            
            # استخراج إشارة AI
            ai_signal = ai_analysis.get('signal', 'NO_TRADE')
            ai_confidence = ai_analysis.get('confidence', 0)
            
            # التحقق من مستوى الثقة
            if ai_confidence < self.min_confidence:
                return self.create_no_trade_signal(
                    pair=pair,
                    reason=f"ثقة منخفضة ({ai_confidence}% < {self.min_confidence}%)",
                    confidence=ai_confidence
                )
            
            # تطبيق قواعد التحقق
            if not self.validate_signal(ai_signal, indicators, ai_confidence):
                return self.create_no_trade_signal(
                    pair=pair,
                    reason="فشل التحقق من القواعد",
                    confidence=ai_confidence
                )
            
            # إنشاء إشارة
            signal_data = {
                'pair': pair,
                'timeframe': timeframe,
                'signal': ai_signal,
                'confidence': ai_confidence,
                'trend': indicators.get('trend', 'N/A'),
                'momentum': ai_analysis.get('momentum', 'N/A'),
                'volatility': indicators.get('volatility_level', 'N/A'),
                'price': market_data.get('current_price', 0),
                'reason': ai_analysis.get('reason', ''),
                'timestamp': market_data.get('timestamp'),
                'indicators': indicators
            }
            
            return signal_data
            
        except Exception as e:
            logger.error(f"خطأ في توليد الإشارة: {e}")
            return self.create_no_trade_signal(
                pair=pair,
                reason=f"خطأ تقني: {str(e)}",
                confidence=0
            )
    
    def validate_signal(self, signal: str, indicators: Dict, confidence: int) -> bool:
        """التحقق من صحة الإشارة"""
        # قواعد أساسية للتحقق
        if signal == 'NO_TRADE':
            return False
        
        if confidence < self.min_confidence:
            return False
        
        # تحقق من التذبذب العالي
        volatility = indicators.get('volatility_level', 'LOW')
        if volatility == 'HIGH' and confidence < 80:
            return False
        
        # تحقق من تناقض الاتجاه مع الإشارة
        trend = indicators.get('trend', '')
        if (signal == 'BUY' and trend == 'DOWN' and confidence < 70) or \
           (signal == 'SELL' and trend == 'UP' and confidence < 70):
            return False
        
        return True
    
    def create_no_trade_signal(self, pair: str, reason: str, confidence: int) -> Dict:
        """إنشاء إشارة عدم تداول"""
        return {
            'pair': pair,
            'signal': 'NO_TRADE',
            'confidence': confidence,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        }
