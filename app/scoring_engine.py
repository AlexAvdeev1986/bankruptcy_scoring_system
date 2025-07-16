import logging
from datetime import datetime, timedelta
from typing import Dict

logger = logging.getLogger(__name__)

class ScoringEngine:
    def __init__(self):
        self.reasons = []
    
    async def calculate_score(self, lead: Dict, request: Dict) -> Dict:
        """Расчет скоринга для лида"""
        try:
            self.reasons = []  # Сброс причин
            score = 0
            
            # Основные правила скоринга
            score += self._calculate_debt_score(lead, request)
            score += self._calculate_debt_type_score(lead, request)
            score += self._calculate_property_score(lead, request)
            score += self._calculate_court_order_score(lead, request)
            score += self._calculate_bankruptcy_score(lead, request)
            score += self._calculate_inn_score(lead, request)
            score += self._calculate_multiple_debts_score(lead)
            
            # Ограничение баллов в диапазоне 0-100
            score = max(0, min(100, score))
            
            # Определение is_target
            is_target = 1 if score >= 50 else 0
            
            # Определение группы для A/B тестов
            group = self._determine_group(lead)
            
            return {
                **lead,
                'score': score,
                'reason_1': self.reasons[0] if len(self.reasons) > 0 else '',
                'reason_2': self.reasons[1] if len(self.reasons) > 1 else '',
                'reason_3': self.reasons[2] if len(self.reasons) > 2 else '',
                'is_target': is_target,
                'group': group
            }
            
        except Exception as e:
            logger.error(f"Scoring calculation error: {e}")
            return {
                **lead,
                'score': 0,
                'reason_1': 'Calculation error',
                'is_target': 0
            }
    
    def _add_reason(self, reason: str):
        """Добавление причины в список"""
        if len(self.reasons) < 3:
            self.reasons.append(reason)
    
    def _calculate_debt_score(self, lead: Dict, request: Dict) -> int:
        """Расчет баллов за сумму долга"""
        debt = lead.get('fssp_debt_amount', 0)
        min_debt = request.get('min_debt', 250000)
        
        if debt > min_debt:
            self._add_reason(f"Сумма долга > {min_debt:,} руб")
            return 30
        elif debt < 100000:
            self._add_reason("Долг < 100,000 руб")
            return -15
        return 0
    
    def _calculate_debt_type_score(self, lead: Dict, request: Dict) -> int:
        """Расчет баллов за тип долга"""
        debt_type = lead.get('fssp_debt_type', '')
        
        if debt_type in ['bank', 'mfo']:
            self._add_reason("Долг от банка/МФО")
            return 20
        elif debt_type in ['tax', 'utility']:
            self._add_reason("Налоговые/ЖКХ долги")
            return -10
        return 0
    
    def _calculate_property_score(self, lead: Dict, request: Dict) -> int:
        """Расчет баллов за наличие имущества"""
        has_property = lead.get('rosreestr_has_property', False)
        
        if not has_property:
            self._add_reason("Нет имущества")
            return 10
        return 0
    
    def _calculate_court_order_score(self, lead: Dict, request: Dict) -> int:
        """Расчет баллов за судебные приказы"""
        has_court_order = lead.get('court_has_order', False)
        court_date = lead.get('court_order_date', '')
        
        if has_court_order and court_date:
            try:
                order_date = datetime.fromisoformat(court_date)
                if datetime.now() - order_date < timedelta(days=90):
                    self._add_reason("Судебный приказ (последние 3 мес)")
                    return 15
            except:
                pass
        return 0
    
    def _calculate_bankruptcy_score(self, lead: Dict, request: Dict) -> int:
        """Расчет баллов за статус банкротства"""
        is_bankrupt = lead.get('fedresurs_is_bankrupt', False)
        
        if is_bankrupt:
            self._add_reason("Признан банкротом")
            return -100
        
        # +10 если нет признаков банкротства
        if not is_bankrupt:
            self._add_reason("Нет признаков банкротства")
            return 10
        return 0
    
    def _calculate_inn_score(self, lead: Dict, request: Dict) -> int:
        """Расчет баллов за статус ИНН"""
        # Получаем статус ИНН
        inn_status = lead.get('inn_status', 'active')
        
        if inn_status == 'active':
            self._add_reason("Активный ИНН")
            return 5
        else:
            self._add_reason("Неактивный ИНН")
            return -100
    
    def _calculate_multiple_debts_score(self, lead: Dict) -> int:
        """Расчет баллов за несколько долгов"""
        # В реальной системе здесь анализировалось бы количество долгов
        # Для демонстрации используем эвристику
        debt_count = lead.get('fssp_debt_count', 1)
        
        if debt_count > 2:
            self._add_reason("Множественные долги")
            return 5
        return 0
    
    def _determine_group(self, lead: Dict) -> str:
        """Определение группы для A/B тестирования"""
        debt = lead.get('fssp_debt_amount', 0)
        has_court = lead.get('court_has_order', False)
        has_property = lead.get('rosreestr_has_property', False)
        debt_type = lead.get('fssp_debt_type', '')
        
        if debt > 500000 and has_court:
            return "high_debt_recent_court"
        elif debt_type in ['bank', 'mfo'] and not has_property:
            return "bank_only_no_property"
        elif debt_type in ['tax', 'utility'] and has_property:
            return "tax_debt_with_property"
        elif debt > 300000 and debt_type not in ['tax', 'utility']:
            return "multiple_creditors"
        
        return "default_group"
    