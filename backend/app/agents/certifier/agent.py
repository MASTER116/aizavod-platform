"""
CERTIFIER — консалтинговый агент по сертификации ТС ЕАЭС.
Демо-версия: rule-based ответы без LLM.
При подключении Ollama заменится на RAG + LLM.
"""

# База знаний: ТР ТС, применимые к автомобилям
TR_TS_DATABASE = {
    "018": {
        "name": "ТР ТС 018/2011",
        "title": "О безопасности колёсных транспортных средств",
        "applies_to": "Все колёсные ТС категорий L, M, N, O",
        "documents": [
            "Заявка на сертификацию",
            "Техническая документация на ТС",
            "Одобрение типа ТС (ОТТС) или свидетельство о безопасности конструкции (СБКТС)",
            "Протоколы испытаний",
        ],
        "cost_range": "150 000 — 2 000 000 руб.",
        "duration": "2-6 месяцев",
    },
    "017": {
        "name": "ТР ТС 017/2011",
        "title": "О безопасности продукции лёгкой промышленности",
        "applies_to": "Комплектующие из текстиля, кожи",
        "documents": ["Протоколы испытаний", "Декларация о соответствии"],
        "cost_range": "30 000 — 100 000 руб.",
        "duration": "1-2 месяца",
    },
    "020": {
        "name": "ТР ТС 020/2011",
        "title": "Электромагнитная совместимость технических средств",
        "applies_to": "Электронные компоненты ТС, бортовое оборудование",
        "documents": ["Протоколы испытаний ЭМС", "Декларация о соответствии"],
        "cost_range": "50 000 — 300 000 руб.",
        "duration": "1-3 месяца",
    },
}

# Страны ЕАЭС для кросс-юрисдикционного анализа
EAEU_COUNTRIES = {
    "russia": {"name": "Россия", "speed": "средняя", "cost_modifier": 1.0},
    "kazakhstan": {"name": "Казахстан", "speed": "быстрее", "cost_modifier": 0.7},
    "belarus": {"name": "Беларусь", "speed": "средняя", "cost_modifier": 0.8},
    "kyrgyzstan": {"name": "Кыргызстан", "speed": "быстрее", "cost_modifier": 0.6},
}

# Ведомственные требования для спецтехники
SPECIAL_REQUIREMENTS = {
    "police": {
        "department": "МВД",
        "extra_certs": ["Сертификация СТП (специальное транспортное средство полиции)", "Проверка установки спецсигналов (маячки, сирена)", "Сертификация перегородки салона"],
        "notes": "Требуется согласование с НИЦ БДД МВД РФ",
    },
    "ambulance": {
        "department": "Минздрав",
        "extra_certs": ["ГОСТ 32828-2014 (автомобили скорой помощи)", "Сертификация медицинского оборудования"],
        "notes": "Класс A/B/C скорой помощи определяет объём сертификации",
    },
    "armored": {
        "department": "Минобороны / ЦБ РФ",
        "extra_certs": ["Сертификация бронезащиты по ГОСТ Р 50963", "Проверка инкассаторского оборудования"],
        "notes": "Отдельная процедура для спецсредств защиты",
    },
}


def process_query(query: str) -> dict:
    """Обработка запроса к CERTIFIER. Демо-версия без LLM."""
    query_lower = query.lower()

    # Определяем тип запроса
    if any(word in query_lower for word in ["сертификат", "сертификация", "тр тс", "одобрение"]):
        return _handle_certification_query(query_lower)
    elif any(word in query_lower for word in ["документ", "бумаг", "подготовить"]):
        return _handle_documents_query(query_lower)
    elif any(word in query_lower for word in ["стоимость", "цена", "сколько стоит", "бюджет"]):
        return _handle_cost_query(query_lower)
    elif any(word in query_lower for word in ["срок", "время", "длительность", "сколько времени"]):
        return _handle_duration_query(query_lower)
    elif any(word in query_lower for word in ["полиц", "мвд", "скорая", "инкассатор", "броне"]):
        return _handle_special_vehicle_query(query_lower)
    else:
        return _handle_general_query(query)


def _handle_certification_query(query: str) -> dict:
    applicable = []
    for code, info in TR_TS_DATABASE.items():
        if "колёс" in info["applies_to"].lower() or "все" in info["applies_to"].lower():
            applicable.append(info)

    response_parts = ["**Применимые технические регламенты:**\n"]
    for reg in applicable:
        response_parts.append(f"- **{reg['name']}** — {reg['title']}")
        response_parts.append(f"  Применяется к: {reg['applies_to']}")
        response_parts.append(f"  Стоимость: {reg['cost_range']}")
        response_parts.append(f"  Сроки: {reg['duration']}\n")

    response_parts.append("\n**Кросс-юрисдикционный анализ ЕАЭС:**")
    response_parts.append("Сертификат ЕАЭС, полученный в любой стране-участнице, действует во всех странах ЕАЭС.")
    for country in EAEU_COUNTRIES.values():
        modifier = country["cost_modifier"]
        response_parts.append(f"- {country['name']}: скорость — {country['speed']}, стоимость ~{int(modifier*100)}% от российской")

    return {
        "agent": "CERTIFIER",
        "response": "\n".join(response_parts),
        "confidence": 0.85,
        "source": "rule-based (демо-режим, без LLM)",
    }


def _handle_documents_query(query: str) -> dict:
    docs = [
        "1. Заявка на проведение сертификации",
        "2. Техническая документация (конструкторская документация, ТУ)",
        "3. Описание транспортного средства (марка, модель, VIN, год, характеристики)",
        "4. Копия ОГРН и ИНН заявителя",
        "5. Контракт на поставку / договор с производителем",
        "6. Ранее полученные сертификаты (если есть)",
        "7. Протоколы испытаний (если проводились)",
    ]
    return {
        "agent": "CERTIFIER",
        "response": "**Базовый пакет документов для сертификации ТС:**\n\n" + "\n".join(docs),
        "confidence": 0.9,
        "source": "rule-based (демо-режим, без LLM)",
    }


def _handle_cost_query(query: str) -> dict:
    return {
        "agent": "CERTIFIER",
        "response": (
            "**Ориентировочная стоимость сертификации ТС ЕАЭС:**\n\n"
            "- Базовая сертификация (ТР ТС 018): 150 000 — 2 000 000 руб.\n"
            "- ЭМС (ТР ТС 020): 50 000 — 300 000 руб.\n"
            "- Малая серия (до 20 шт.): от 100 000 руб.\n"
            "- Массовая серия (30 000+ шт.): от 500 000 руб.\n\n"
            "**Экономия через ЕАЭС:**\n"
            "- Казахстан: ~70% от российской стоимости\n"
            "- Кыргызстан: ~60% от российской стоимости\n"
            "- Сертификат действует во всех странах ЕАЭС\n\n"
            "*Точная стоимость зависит от типа ТС, объёма партии и лаборатории.*"
        ),
        "confidence": 0.8,
        "source": "rule-based (демо-режим, без LLM)",
    }


def _handle_duration_query(query: str) -> dict:
    return {
        "agent": "CERTIFIER",
        "response": (
            "**Сроки сертификации ТС ЕАЭС:**\n\n"
            "- ОТТС (одобрение типа): 3-6 месяцев\n"
            "- СБКТС (единичное ТС): 1-3 месяца\n"
            "- Декларация (компоненты): 1-2 месяца\n"
            "- Спецтехника (МВД/Минздрав): +1-2 месяца к базовому сроку\n\n"
            "*Ускоренная процедура возможна в Казахстане и Кыргызстане.*"
        ),
        "confidence": 0.85,
        "source": "rule-based (демо-режим, без LLM)",
    }


def _handle_special_vehicle_query(query: str) -> dict:
    vehicle_type = None
    if any(w in query for w in ["полиц", "мвд"]):
        vehicle_type = "police"
    elif any(w in query for w in ["скорая", "медицин"]):
        vehicle_type = "ambulance"
    elif any(w in query for w in ["инкассатор", "броне"]):
        vehicle_type = "armored"

    if vehicle_type and vehicle_type in SPECIAL_REQUIREMENTS:
        req = SPECIAL_REQUIREMENTS[vehicle_type]
        certs = "\n".join(f"  - {c}" for c in req["extra_certs"])
        return {
            "agent": "CERTIFIER",
            "response": (
                f"**Сертификация спецтехники ({req['department']}):**\n\n"
                f"Помимо базовой сертификации по ТР ТС 018, требуется:\n{certs}\n\n"
                f"**Важно:** {req['notes']}\n\n"
                "Кейс МВД: МАЗ Москвич столкнулся с 2-месячной задержкой именно из-за "
                "неясности ведомственных требований. CERTIFIER решает это за часы."
            ),
            "confidence": 0.85,
            "source": "rule-based (демо-режим, без LLM)",
        }

    return _handle_general_query("спецтехника")


def _handle_general_query(query: str) -> dict:
    return {
        "agent": "CERTIFIER",
        "response": (
            "Я — CERTIFIER, AI-агент по сертификации транспортных средств ЕАЭС.\n\n"
            "Я могу помочь с:\n"
            "- Определением применимых ТР ТС/ЕАЭС\n"
            "- Списком необходимых документов\n"
            "- Оценкой стоимости и сроков\n"
            "- Кросс-юрисдикционным анализом (РФ/Казахстан/Беларусь/Кыргызстан)\n"
            "- Требованиями для спецтехники (МВД, Минздрав, Минобороны)\n\n"
            "Укажи марку, модель, год и назначение ТС — и я дам детальный анализ.\n\n"
            "*Демо-режим: ответы основаны на базе правил. "
            "Полная версия с AI будет использовать RAG + LLM для точных ответов.*"
        ),
        "confidence": 1.0,
        "source": "rule-based (демо-режим, без LLM)",
    }
