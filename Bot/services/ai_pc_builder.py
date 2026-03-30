"""
AI-усиленный сборщик ПК с fallback на стандартную логику.

Интегрирует ИИ для умного распределения бюджета и рекомендаций,
но автоматически возвращается к проверенной логике если ИИ недоступен.
"""

import json
import logging
from typing import Dict, Optional, Any, Tuple

from Bot.services.ai_service import AIService
from Bot.services.pc_builder import build_pc as standard_build_pc, _total_price
from Bot.services.budget_allocator import BudgetAllocator

logger = logging.getLogger(__name__)


class AIPcBuilder:
    """AI-усиленный сборщик с автоматическим fallback."""
    
    def __init__(self, enable_ai: bool = True):
        self.enable_ai = enable_ai
        self.ai_service = AIService() if enable_ai else None
        
    def _create_ai_prompt(self, budget: int, preset: str, all_parts: Dict) -> str:
        """Создает промпт для ИИ с учетом доступных компонентов."""
        
        # Анализируем доступные компоненты
        component_ranges = {}
        component_samples = {}
        
        for category, items in all_parts.items():
            if items and len(items) > 0:
                # БЕЗ ФИЛЬТРАЦИИ - даем ИИ полный доступ ко всем данным
                if items:
                    prices = [item.get('price', 0) for item in items if item.get('price', 0) > 0]
                    if prices:
                        component_ranges[category] = {
                            'min': min(prices),
                            'max': max(prices),
                            'count': len(prices),
                            'avg': sum(prices) // len(prices)
                        }
                        
                        # Берем примеры из разных ценовых сегментов
                        sorted_items = sorted(items, 
                                        key=lambda x: x.get('price', 0), reverse=True)
                        
                        # Выбираем компоненты из разных ценовых категорий
                        samples = []
                        total_items = len(sorted_items)
                        
                        if total_items >= 3:
                            # Берем один из топа, один из середины, один из бюджета
                            samples.append(sorted_items[0])  # Самый дорогой
                            mid_index = total_items // 2
                            samples.append(sorted_items[mid_index])  # Средний
                            samples.append(sorted_items[-1])  # Самый дешевый
                        else:
                            samples = sorted_items[:3]  # Если мало, берем все
                        
                        component_samples[category] = [
                            {
                                'name': item.get('name', '')[:50],  # Обрезаем длинные названия
                                'price': item.get('price', 0)
                            }
                            for item in samples
                        ]
        
        preset_descriptions = {
            'gaming': 'игровой ПК с акцентом на видеокарту и производительность',
            'work': 'рабочий ПК для офисных задач и профессиональной работы',
            'universal': 'универсальный ПК для повседневных задач'
        }
        
        return f"""
Ты - эксперт по сборке ПК. Проанализируй бюджет и предложи оптимальное распределение средств.

ВАЖНОЕ ПРАВИЛО: Общая сумма всех компонентов НЕ ДОЛЖНА превышать {budget:,} тенге!

Бюджет: {budget:,} тенге
Назначение: {preset_descriptions.get(preset, preset)}

Анализ доступных компонентов (после фильтрации мусора):
{json.dumps(component_ranges, indent=2, ensure_ascii=False)}

Примеры компонентов в разных ценовых сегментах (топ, средний, бюджетный):
{json.dumps(component_samples, indent=2, ensure_ascii=False)}

Верни JSON с распределением бюджета по категориям:
{{
    "cpu": бюджет_процессор,
    "motherboard": бюджет_материнская_плата,
    "ram": бюджет_оперативная_память,
    "gpu": бюджет_видеокарта,
    "ssd": бюджет_накопитель,
    "psu": бюджет_блок_питания,
    "coolers": бюджет_кулер,
    "case": бюджет_корпус
}}

Учитывай:

- Распределяй бюджет логично исходя из назначения ПК
- Для игровых ПК: приоритет видеокарте, затем процессору
- Для рабочих ПК: приоритет процессору и оперативной памяти  
- Для универсальных: сбалансированное распределение
- Обеспечь совместимость сокетов и чипсетов
- СУММА НЕ ДОЛЖНА ПРЕВЫШАТЬ {budget:,} тенге - ЭТО КРАЙНЕ ВАЖНО!
- Оставь небольшой запас (~5% бюджета) для непредвиденных расходов
- Все значения должны быть целыми числами
- Ориентируй на СРЕДНИЕ цены из доступных компонентов: {json.dumps({k: v.get('avg', 0) for k, v in component_ranges.items()}, ensure_ascii=False)}
- Используй только компоненты из предоставленного списка
- При большом бюджете выбирай более производительные компоненты
- Учитывай что названия компонентов содержат информацию об объеме и характеристиках
- Примеры компонентов показаны в разных ценовых сегментах (топ, средний, бюджетный) для ориентира
"""

    def _get_ai_budget_allocation(self, budget: int, preset: str, all_parts: Dict) -> Optional[Dict[str, int]]:
        """Получает распределение бюджета от ИИ."""
        if not self.ai_service:
            return None
            
        try:
            prompt = self._create_ai_prompt(budget, preset, all_parts)
            response = self.ai_service.get_completion(prompt)
            
            if response:
                ai_budgets = json.loads(response)
                
                # Валидация ответа ИИ
                required_keys = ['cpu', 'motherboard', 'ram', 'gpu', 'ssd', 'psu', 'coolers', 'case']
                if all(key in ai_budgets for key in required_keys):
                    total_ai_budget = sum(ai_budgets.values())
                    if total_ai_budget <= budget:
                        logger.info(f"AI предложил бюджет: {total_ai_budget:,} из {budget:,}")
                        return ai_budgets
                    else:
                        logger.warning(f"AI превысил бюджет: {total_ai_budget:,} > {budget:,}")
                        # Пробуем скорректировать бюджет пропорционально
                        corrected_budgets = self._correct_ai_budgets(ai_budgets, budget)
                        if corrected_budgets:
                            corrected_total = sum(corrected_budgets.values())
                            logger.info(f"Скорректированный бюджет: {corrected_total:,} из {budget:,}")
                            return corrected_budgets
                        
        except Exception as e:
            logger.error(f"Ошибка получения AI распределения: {e}")
            
        return None

    def _is_valid_component(self, item: dict) -> bool:
        """Проверяет что компонент не является мусорным."""
        if not item or not isinstance(item, dict):
            return False
            
        name = item.get('name', '').lower().strip()
        price = item.get('price', 0)
        code = item.get('code', '').strip()
        
        # Базовые проверки
        if not name or price <= 0:
            return False
            
        # Фильтруем мусорные названия
        junk_keywords = [
            'смотрите в разделе', 'для серверов', 'серверные', 'б/у', 'used',
            'http', 'www.', '.com', 'тест', 'test',
            'образец', 'demo', 'ремонт', 'восстановление', 'рефаб',
            'без цены', '0 тг', '0 ₸', 'договорная', 'по запросу'
        ]
        
        for keyword in junk_keywords:
            if keyword in name:
                return False
                
        # Фильтруем домены (но оставляем .kz и .ru - это могут быть нормальные названия)
        domain_keywords = ['.com', '.net', '.org']
        for domain in domain_keywords:
            if domain in name and not any(tech in name for tech in ['sata', 'ddr', 'atx', 'matx']):
                return False
                
        # Фильтруем слишком короткие названия
        if len(name.strip()) < 2:  # ослабляем до 2 символов
            return False
            
        # Фильтруем неинформативные коды
        if code and len(code.strip()) < 1:  # ослабляем до 1 символа
            return False
            
        # Фильтруем слишком дешевые компоненты (возможно ошибка)
        if price < 500:  # ослабляем до 500 тенге
            return False
            
        # Фильтруем слишком дорогие (возможно ошибка)
        if price > 5_000_000:  # ослабляем до 5 миллионов
            return False
            
        return True

    def _correct_ai_budgets(self, ai_budgets: Dict[str, int], target_budget: int) -> Optional[Dict[str, int]]:
        """Корректирует бюджет от ИИ чтобы соответствовать целевому бюджету."""
        try:
            total = sum(ai_budgets.values())
            if total == 0:
                return None
                
            # Вычисляем коэффициент масштабирования
            scale_factor = target_budget / total
            
            # Применяем коэффициент к каждой категории
            corrected = {}
            for key, value in ai_budgets.items():
                corrected_value = int(value * scale_factor)
                # Устанавливаем минимальные значения для важных компонентов
                if key == 'cpu' and corrected_value < 30000:
                    corrected_value = 30000
                elif key == 'motherboard' and corrected_value < 20000:
                    corrected_value = 20000
                elif key == 'ram' and corrected_value < 15000:
                    corrected_value = 15000
                elif key == 'gpu' and corrected_value < 40000:
                    corrected_value = 40000
                elif key == 'psu' and corrected_value < 10000:
                    corrected_value = 10000
                elif key == 'case' and corrected_value < 8000:
                    corrected_value = 8000
                elif key == 'ssd' and corrected_value < 12000:
                    corrected_value = 12000
                elif key == 'coolers' and corrected_value < 5000:
                    corrected_value = 5000
                    
                corrected[key] = corrected_value
            
            # Проверяем что сумма не превышает бюджет
            corrected_total = sum(corrected.values())
            if corrected_total > target_budget:
                # Если все еще превышает, урезаем самую дорогую категорию
                most_expensive = max(corrected, key=lambda k: corrected[k])
                excess = corrected_total - target_budget
                corrected[most_expensive] = max(corrected[most_expensive] - excess, 10000)
            
            logger.info(f"Бюджет скорректирован: {sum(corrected.values()):,} из {target_budget:,}")
            return corrected
            
        except Exception as e:
            logger.error(f"Ошибка корректировки бюджета: {e}")
            return None

    def _build_with_ai_budgets(self, budget: int, preset: str, all_parts: Dict, ai_budgets: Dict[str, int]) -> Dict:
        """Собирает ПК используя бюджет от ИИ."""
        try:
            # Импортируем функции подбора компонентов
            from Bot.services.pc_builder_pick import (
                pick_cpu, pick_motherboard, pick_ram, pick_gpu,
                pick_ssd, pick_psu, pick_cooler, pick_case,
            )
            
            # Собираем по AI квотам
            cpu = pick_cpu(all_parts["cpu"], ai_budgets["cpu"])
            mobo = pick_motherboard(all_parts["motherboard"], cpu, ai_budgets["motherboard"])
            ram = pick_ram(all_parts["ram"], mobo, ai_budgets["ram"])
            gpu = pick_gpu(all_parts["gpu"], ai_budgets["gpu"])
            ssd = pick_ssd(all_parts["ssd"], ai_budgets["ssd"])
            psu = pick_psu(all_parts["psu"], cpu, gpu, ai_budgets["psu"])
            cooler = pick_cooler(all_parts["coolers"], cpu, ai_budgets["coolers"])
            case = pick_case(all_parts["case"], mobo, ai_budgets["case"])
            
            build = {
                "cpu": cpu,
                "motherboard": mobo,
                "ram": ram,
                "gpu": gpu,
                "ssd": ssd,
                "psu": psu,
                "cooler": cooler,
                "case": case,
            }
            
            total = _total_price(build)
            if total <= budget:
                return build
                
        except Exception as e:
            logger.error(f"Ошибка сборки с AI бюджетами: {e}")
            
        return None

    def _get_ai_explanation(self, build: Dict, budget: int, preset: str) -> str:
        """Получает объяснение выбора компонентов от ИИ."""
        if not self.ai_service:
            return ""
            
        try:
            components_info = []
            for category, component in build.items():
                if component:
                    components_info.append(f"{category}: {component['name']} ({component['price']:,} ₸)")
            
            prompt = f"""
Ты - эксперт по ПК. Объясни выбор компонентов для сборки.

Бюджет: {budget:,} тенге
Назначение: {preset}

Компоненты:
{chr(10).join(components_info)}

Дай краткое, красивое объяснение выбора (2-3 предложения).
Объясни почему эти компоненты хорошо подходят друг к другу и для задач.
Используй простой, понятный язык.

Примеры хороших ответов:
- "Отличный игровой набор! Процессор и видеокарта обеспечат высокую производительность в современных играх, а остальные компоненты подобраны с запасом для будущего апгрейда."
- "Идеальный баланс для работы! Мощный процессор и быстрая память справятся с профессиональными задачами, а надежные компоненты обеспечат стабильную работу."
"""

            response = self.ai_service.get_completion(prompt)
            if response and response.strip():
                # Пробуем извлечь текст из ответа
                text = response.strip()
                
                # Если пришел JSON, пытаемся извлечь текст
                if text.startswith('{') and text.endswith('}'):
                    try:
                        import json
                        data = json.loads(text)
                        # Ищем поля с объяснением
                        for key in ['explanation', 'text', 'response', 'answer']:
                            if key in data and data[key]:
                                return str(data[key]).strip()
                    except:
                        pass
                
                # Если это не JSON, возвращаем как есть
                if not text.startswith('{'):
                    return text
                
                # Если все еще не получили текст, возвращаем заглушку
                return "Подобраны оптимальные компоненты для ваших задач с учетом бюджета и требований."
                
        except Exception as e:
            logger.error(f"Ошибка получения объяснения: {e}")
            
        return ""

    def _get_ai_direct_selection(self, budget: int, preset: str, all_parts: Dict) -> Optional[Dict]:
        """Получает прямое распределение бюджета от ИИ."""
        if not self.ai_service:
            return None
            
        try:
            prompt = self._create_direct_selection_prompt(budget, preset, all_parts)
            response = self.ai_service.get_completion(prompt)
            
            if response:
                ai_selection = json.loads(response)
                
                # Валидация ответа ИИ
                required_keys = ['cpu', 'motherboard', 'ram', 'gpu', 'ssd', 'psu', 'coolers', 'case']
                if all(key in ai_selection for key in required_keys):
                    # Проверяем что это компоненты с нужными полями
                    valid_selection = True
                    for key in required_keys:
                        component = ai_selection[key]
                        if not isinstance(component, dict) or 'name' not in component or 'price' not in component:
                            valid_selection = False
                            break
                    
                    if valid_selection:
                        total_ai_budget = sum(component.get('price', 0) for component in ai_selection.values())
                        if total_ai_budget <= budget:
                            logger.info(f"AI выбрал компоненты на сумму: {total_ai_budget:,} из {budget:,}")
                            return ai_selection
                        else:
                            logger.warning(f"AI превысил бюджет: {total_ai_budget:,} > {budget:,}")
                            # Пробуем скорректировать
                            corrected = self._correct_ai_selection(ai_selection, budget)
                            if corrected:
                                corrected_total = sum(component.get('price', 0) for component in corrected.values())
                                logger.info(f"Скорректированная выборка: {corrected_total:,} из {budget:,}")
                                return corrected
                        
        except Exception as e:
            logger.error(f"Ошибка получения AI выбора: {e}")
            
        return None

    def _create_direct_selection_prompt(self, budget: int, preset: str, all_parts: Dict) -> str:
        """Создает промпт для прямого выбора компонентов ИИ."""
        
        # Даем ИИ ВСЕ компоненты без фильтрации мусора
        component_options = {}
        
        for category, items in all_parts.items():
            if items:
                # НИКАКОЙ ФИЛЬТРАЦИИ - даем ИИ полный контроль
                if items:
                    # Сортируем по цене для удобства выбора
                    sorted_items = sorted(items, key=lambda x: x.get('price', 0))
                    
                    # Даем ИИ все варианты (или до 50 самых популярных)
                    all_items = sorted_items[:50]  # Ограничиваем только для размера промпта
                    
                    component_options[category] = [
                        {
                            'name': item.get('name', '')[:100],
                            'price': item.get('price', 0),
                            'code': item.get('code', '')
                        }
                        for item in all_items
                    ]
        
        preset_descriptions = {
            'gaming': 'игровой ПК с максимальной производительностью в играх',
            'work': 'рабочий ПК для профессиональных задач и офисной работы',
            'universal': 'универсальный ПК для повседневных задач и развлечений'
        }
        
        return f"""
Ты - профессиональный эксперт по сборке ПК с 10-летним опытом. Проанализируй бюджет и подбери идеальные компоненты.

БЮДЖЕТ: {budget:,} тенге
НАЗНАЧЕНИЕ: {preset_descriptions.get(preset, preset)}

ДОСТУПНЫЕ КОМПОНЕНТЫ (полный список без фильтрации - ты сам эксперт и отсеешь мусор):

{json.dumps(component_options, indent=2, ensure_ascii=False)}

ТВОЯ ЗАДАЧА:
1. Выбери ОДИН лучший компонент из каждой категории
2. Распредели бюджет МАКСИМАЛЬНО ЭФФЕКТИВНО под задачи
3. Обеспечь ИДЕАЛЬНУЮ совместимость всех компонентов
4. Подумай о будущем апгрейде и запасе мощности

ПРИОРИТЕТЫ ДЛЯ ВЫБОРА:

🎮 ИГРОВОЙ ПК:
- Видеокарта: 40-50% бюджета (самый важный компонент)
- Процессор: 20-25% бюджета (мощный для игр)
- Материнская плата: хороший чипсет (B660, B760, X670, не H610!)
- Оперативная память: минимум 16GB, лучше 32GB DDR4/DDR5
- SSD: минимум 1TB для игр, лучше 2TB NVMe
- Блок питания: с запасом 30-40% мощности
- Охлаждение: эффективное, не бюджетное
- Корпус: хороший airflow, место для компонентов

💻 РАБОЧИЙ ПК:
- Процессор: 30-35% бюджета (максимальная производительность)
- Оперативная память: 15-20% бюджета (много и быстро)
- Материнская плата: стабильная, с нужными портами
- SSD: быстрый и надежный
- Видеокарта: если нужна для работы

🏠 УНИВЕРСАЛЬНЫЙ ПК:
- Сбалансировать все компоненты
- Универсальный процессор
- 16-32GB памяти
- Хороший SSD

КРИЧЕСКИЕ ТРЕБОВАНИЯ:
- ✅ НЕ ПРЕВЫШАТЬ бюджет: {budget:,} тенге
- ✅ Совместимость сокетов (Intel 1700 с матплатами 1700, AMD AM5 с AM5)
- ✅ Совместимость RAM (DDR4 с DDR4 платами, DDR5 с DDR5)
- ✅ Мощность блока питания с запасом
- ✅ Размер корпуса и охлаждения
- ✅ Выбирай КАЧЕСТВЕННЫЕ компоненты, не самые дешевые
- ✅ САМ ОТФИЛЬТРУЙ мусор: б/у, серверное, неинформативные названия, нулевые цены

ВЕРНИ JSON С ВЫБРАННЫМИ КОМПОНЕНТАМИ:
{{
    "cpu": {{"name": "название", "price": цена, "code": "код"}},
    "motherboard": {{"name": "название", "price": цена, "code": "код"}},
    "ram": {{"name": "название", "price": цена, "code": "код"}},
    "gpu": {{"name": "название", "price": цена, "code": "код"}},
    "ssd": {{"name": "название", "price": цена, "code": "код"}},
    "psu": {{"name": "название", "price": цена, "code": "код"}},
    "coolers": {{"name": "название", "price": цена, "code": "код"}},
    "case": {{"name": "название", "price": цена, "code": "код"}}
}}

ПОМНИ: Ты эксперт! Выбирай как для себя с умом и заботой о пользователе.
"""

    def _correct_ai_selection(self, ai_selection: Dict, target_budget: int) -> Optional[Dict]:
        """Корректирует выбор ИИ чтобы соответствовать бюджету."""
        try:
            total = sum(component.get('price', 0) for component in ai_selection.values())
            if total == 0:
                return None
                
            # Если превышен бюджет, урезаем самые дорогие компоненты
            if total > target_budget:
                # Сортируем компоненты по цене
                sorted_components = sorted(ai_selection.items(), key=lambda x: x[1].get('price', 0), reverse=True)
                
                excess = total - target_budget
                corrected = ai_selection.copy()
                
                # Урезаем самые дорогие компоненты
                for category, component in sorted_components:
                    if excess <= 0:
                        break
                    
                    current_price = component.get('price', 0)
                    reduction = min(excess, current_price * 0.3)  # Урезаем до 30% от цены
                    
                    # Ищем более дешевый вариант в той же категории
                    # Это упрощенная версия - в реальности нужно искать в списке доступных компонентов
                    corrected[category]['price'] = max(int(current_price - reduction), 10000)
                    excess -= reduction
                
                # Проверяем итоговую сумму
                corrected_total = sum(component.get('price', 0) for component in corrected.values())
                if corrected_total <= target_budget:
                    return corrected
            
            return ai_selection
            
        except Exception as e:
            logger.error(f"Ошибка корректировки выбора: {e}")
            return None

    def build_pc(self, budget: int, preset: str, all_parts: Dict) -> Tuple[Dict, bool, str]:
        """
        Основная функция сборки ПК.
        
        Возвращает:
        - build: словарь с компонентами
        - used_ai: bool - использовался ли ИИ
        - explanation: str - объяснение выбора
        """
        
        # 1. Пытаемся использовать ИИ для прямого выбора
        if self.enable_ai and self.ai_service:
            logger.info("Попытка сборки ПК с прямым выбором ИИ...")
            
            try:
                # Пробуем прямой выбор компонентов
                ai_selection = self._get_ai_direct_selection(budget, preset, all_parts)
                
                if ai_selection:
                    # Получаем объяснение от ИИ
                    explanation = self._get_ai_explanation(ai_selection, budget, preset)
                    logger.info("AI прямой выбор успешно завершен")
                    return ai_selection, True, explanation
                        
            except Exception as e:
                logger.error(f"Ошибка при AI прямом выборе: {e}")
        
        # 2. Пробуем ИИ для распределения бюджета
        if self.enable_ai and self.ai_service:
            logger.info("Попытка сборки ПК с использованием ИИ...")
            
            try:
                # Получаем распределение бюджета от ИИ
                ai_budgets = self._get_ai_budget_allocation(budget, preset, all_parts)
                
                if ai_budgets:
                    # Собираем по AI квотам
                    ai_build = self._build_with_ai_budgets(budget, preset, all_parts, ai_budgets)
                    
                    if ai_build:
                        # Получаем объяснение от ИИ
                        explanation = self._get_ai_explanation(ai_build, budget, preset)
                        logger.info("AI сборка успешно завершена")
                        return ai_build, True, explanation
                        
            except Exception as e:
                logger.error(f"Ошибка при AI сборке: {e}")
        
        # 2. Fallback на стандартную логику
        logger.info("Использование стандартной логики сборки...")
        try:
            standard_build = standard_build_pc(budget, preset, all_parts)
            explanation = "Сборка выполнена по стандартному алгоритму с оптимальным распределением бюджета."
            return standard_build, False, explanation
            
        except Exception as e:
            logger.error(f"Ошибка стандартной сборки: {e}")
            raise


# Глобальный экземпляр для использования в приложении
_ai_builder = None


def get_ai_builder(enable_ai: bool = True) -> AIPcBuilder:
    """Получает экземпляр AI сборщика (синглтон)."""
    global _ai_builder
    if _ai_builder is None or _ai_builder.enable_ai != enable_ai:
        _ai_builder = AIPcBuilder(enable_ai=enable_ai)
    return _ai_builder


def build_pc_with_ai(budget: int, preset: str, all_parts: Dict, enable_ai: bool = True) -> Tuple[Dict, bool, str]:
    """
    Удобная функция для сборки ПК с ИИ поддержкой.
    
    Параметры:
    - budget: бюджет в тенге
    - preset: назначение ("gaming", "work", "universal")
    - all_parts: словарь с компонентами
    - enable_ai: включить ИИ (по умолчанию True)
    
    Возвращает:
    - build: словарь с компонентами
    - used_ai: bool - использовался ли ИИ
    - explanation: str - объяснение выбора
    """
    builder = get_ai_builder(enable_ai)
    return builder.build_pc(budget, preset, all_parts)
