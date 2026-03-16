"""OpportunityScanner — глубокий поиск и анализ конкурсов, грантов, хакатонов.

Полный цикл: поиск → анализ правил → генерация идей под конкурс →
Excel-калькуляция → генерация документов на подачу → сохранение идей.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx

logger = logging.getLogger("aizavod.opportunity_scanner")

# ─── Источники ──────────────────────────────────────────────────────────────

SOURCES: list[dict[str, str]] = [
    # Гранты РФ
    {"name": "ФАСИ (Фонд содействия инновациям)", "url": "https://fasie.ru", "type": "grant",
     "programs": "Старт-ИИ, Развитие-ИИ, Коммерциализация, Бизнес-Старт"},
    {"name": "РНФ (Российский научный фонд)", "url": "https://rscf.ru", "type": "grant",
     "programs": "Малые группы (дедлайн 16.06.2026), Отдельные проекты"},
    {"name": "Фонд Сколково", "url": "https://sk.ru", "type": "grant",
     "programs": "Грант до 5 млн руб. на R&D, микрогранты до 1.5 млн"},
    {"name": "ФСИ (Фонд развития интернет-инициатив)", "url": "https://iidf.ru", "type": "accelerator",
     "programs": "Акселератор, инвестиции до 25 млн руб."},
    {"name": "Платформа НТИ", "url": "https://nti.one", "type": "grant",
     "programs": "Цифровые технологии, ИИ, маркетплейсы НТИ"},
    {"name": "АСИ (Агентство стратегических инициатив)", "url": "https://asi.ru", "type": "competition",
     "programs": "100 лидеров, Сильные идеи для нового времени"},

    # Научные гранты и фонды
    {"name": "РФФИ / РНФ конкурсы", "url": "https://rscf.ru/contests/", "type": "grant",
     "programs": "Научные гранты: фундаментальные и прикладные исследования, молодые учёные"},
    {"name": "Гранты Президента РФ", "url": "https://grants.gov.ru", "type": "grant",
     "programs": "Президентские гранты для НКО, молодых учёных, социальных проектов"},
    {"name": "Фонд Бортника — Старт-ИИ", "url": "https://fasie.ru/programs/", "type": "grant",
     "programs": "Гранты до 8 млн на проекты в сфере ИИ, для малых предприятий"},
    {"name": "Минобрнауки — конкурсы", "url": "https://minobrnauki.gov.ru", "type": "grant",
     "programs": "Научные гранты, мегагранты, программа Приоритет 2030, НИОКР"},
    {"name": "Платформа гранты.рф", "url": "https://гранты.рф", "type": "grant",
     "programs": "Агрегатор всех грантов РФ: научные, социальные, IT, молодёжные"},
    {"name": "Росмолодёжь.Гранты", "url": "https://grants.myrosmol.ru", "type": "grant",
     "programs": "Молодёжные гранты до 1.5 млн, проекты в сфере IT и науки"},
    {"name": "Конкурсы РАН", "url": "https://ras.ru", "type": "competition",
     "programs": "Премии и конкурсы Российской академии наук для молодых учёных"},
    {"name": "Иннопрактика", "url": "https://innopraktika.ru", "type": "grant",
     "programs": "Научно-технологические проекты, трансфер технологий, гранты"},
    {"name": "Национальные проекты", "url": "https://национальныепроекты.рф", "type": "grant",
     "programs": "Цифровая экономика, наука и университеты, субсидии на НИОКР"},

    # Региональные и отраслевые гранты
    {"name": "ФРП (Фонд развития промышленности)", "url": "https://frp.ru", "type": "grant",
     "programs": "Займы и гранты на разработку ПО, цифровизацию производства"},
    {"name": "РФРИТ (Фонд развития IT)", "url": "https://рфрит.рф", "type": "grant",
     "programs": "Гранты на разработку отечественного ПО, до 500 млн руб."},
    {"name": "Центр «Мой бизнес»", "url": "https://мойбизнес.рф", "type": "grant",
     "programs": "Субсидии для МСП, гранты до 500K на ИТ, соцконтракт до 350K"},
    {"name": "Соцконтракт", "url": "https://mintrud.gov.ru", "type": "grant",
     "programs": "Социальный контракт на открытие бизнеса до 350 тыс. руб., безвозмездно"},

    # Хакатоны
    {"name": "Цифровой прорыв", "url": "https://hacks-ai.ru", "type": "hackathon",
     "programs": "Всероссийские хакатоны по ИИ, призы до 3 млн руб."},
    {"name": "Leaders of Digital", "url": "https://leadersofdigital.ru", "type": "hackathon",
     "programs": "IT-хакатоны, цифровая трансформация"},
    {"name": "DevPost", "url": "https://devpost.com/hackathons", "type": "hackathon",
     "programs": "Международные хакатоны (AI, ML, Web3)"},
    {"name": "MLContest", "url": "https://mlcontests.com", "type": "competition",
     "programs": "ML соревнования с призами"},

    # IT-конкурсы и акселераторы РФ
    {"name": "Иннополис", "url": "https://innopolis.com", "type": "accelerator",
     "programs": "Акселератор стартапов, AI/ML трек"},
    {"name": "GenerationS", "url": "https://generations.vc", "type": "accelerator",
     "programs": "Корпоративный акселератор РВК"},
    {"name": "Старт (ФАСИ)", "url": "https://fasie.ru/programs/programma-start/", "type": "grant",
     "programs": "Грант до 4 млн на коммерциализацию результатов НИОКР, для малых предприятий"},

    # Международные
    {"name": "Anthropic Hackathons", "url": "https://anthropic.com", "type": "hackathon",
     "programs": "Хакатоны Claude API"},
    {"name": "Google AI Challenge", "url": "https://ai.google", "type": "competition",
     "programs": "AI/ML соревнования"},
    {"name": "Kaggle", "url": "https://kaggle.com/competitions", "type": "competition",
     "programs": "ML соревнования, призы $10K-$1M"},
]

RELEVANCE_KEYWORDS = [
    "искусственный интеллект", "ИИ", "AI", "нейросет", "машинное обучение",
    "ML", "NLP", "LLM", "чат-бот", "chatbot", "автоматизация", "SaaS",
    "мультиагент", "цифровая трансформация", "цифровизация",
    "стартап", "IT", "ИТ", "программное обеспечение", "ПО",
    "сертификация", "ЕАЭС", "малый бизнес", "МСП",
    "генерация контента", "computer vision", "обработка данных",
    # Научные и образовательные
    "грант", "субсидия", "безвозмездн", "конкурс", "премия",
    "наука", "научн", "исследовани", "НИОКР", "R&D", "НИОКТР",
    "молодой учёный", "молодых учёных", "аспирант", "диссертация",
    "инновац", "технолог", "импортозамещ", "отечественное ПО",
    "социальный контракт", "соцконтракт", "президентский грант",
    "Приоритет 2030", "национальный проект", "цифровая экономика",
]

PARTICIPANT_CONTEXT = """ПРОФИЛЬ УЧАСТНИКА:
- Возраст: 32 года
- Доход: 200 000 руб./мес
- Регион регистрации: Татарстан (Набережные Челны)
- Регион проживания: Москва
- Образование: инженер
- Нет учёной степени, нет научных публикаций, нет аффилиации с вузом/НИИ
- ООО нет (планируется август 2026)
- Бюджет на проекты: 0 руб (только грантовые средства)
- Навыки: IT, программирование, AI/ML (практическое применение)

ВАРИАНТЫ УЧАСТИЯ:
1. Напрямую — как физлицо, ИП или ООО
2. Через вуз/НИИ — как сторонний исполнитель по договору ГПХ (если грант вузовский, но можно привлекать внешних исполнителей)
Если конкурс для вузов — укажи что можно участвовать через ГПХ и какой вуз/НИИ нужно найти."""


@dataclass
class Opportunity:
    title: str
    source: str
    url: str
    type: str  # grant, hackathon, competition, accelerator, tender
    deadline: str = ""
    prize: str = ""
    description: str = ""
    relevance_score: float = 0.0
    ai_analysis: str = ""
    found_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class OpportunityScanner:
    """Глубокий поиск и анализ возможностей для AI Zavod."""

    def __init__(self) -> None:
        self._anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        self._model = os.getenv("SCANNER_MODEL", "claude-haiku-4-5-20251001")
        self._found: list[Opportunity] = []

    async def _call_llm(self, prompt: str, *, max_tokens: int = 3000, temperature: float = 0.4) -> str:
        if not self._anthropic_key:
            return "ANTHROPIC_API_KEY не настроен"
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=self._anthropic_key)
        response = await client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return response.content[0].text

    # ─── 1. Поиск ───────────────────────────────────────────────────────────

    async def _fetch_devpost_hackathons(self) -> list[Opportunity]:
        """Загрузка открытых хакатонов с DevPost через публичный API."""
        results: list[Opportunity] = []
        api_url = "https://devpost.com/api/hackathons"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Загружаем первые 3 страницы (до 27 хакатонов)
                for page in range(1, 4):
                    resp = await client.get(api_url, params={
                        "status": "open",
                        "order_by": "deadline",
                        "page": page,
                    }, headers={"User-Agent": "Mozilla/5.0"})
                    if resp.status_code != 200:
                        break
                    data = resp.json()
                    hackathons = data.get("hackathons", [])
                    if not hackathons:
                        break
                    for h in hackathons:
                        # Убираем HTML из призовой суммы
                        prize_raw = h.get("prize_amount", "") or ""
                        prize = re.sub(r"<[^>]+>", "", prize_raw)
                        title = h.get("title", "").strip()
                        time_left = h.get("time_left_to_submission", "")
                        dates = h.get("submission_period_dates", "")
                        themes = ", ".join(t["name"] for t in h.get("themes", []))
                        desc_parts = []
                        if prize and prize != "$0":
                            desc_parts.append(f"Приз: {prize}")
                        if time_left:
                            desc_parts.append(time_left)
                        if themes:
                            desc_parts.append(themes)
                        if dates:
                            desc_parts.append(dates)

                        results.append(Opportunity(
                            title=title,
                            source="DevPost",
                            url=h.get("url", ""),
                            type="hackathon",
                            prize=prize,
                            deadline=time_left,
                            description=" | ".join(desc_parts),
                        ))
        except Exception as exc:
            logger.warning("DevPost API failed: %s", exc)
        return results

    async def scan_web(self, query: str | None = None) -> list[Opportunity]:
        """Поиск конкурсов и грантов в интернете (без хакатонов — они в отдельной кнопке)."""
        queries = [
            query or "гранты ИИ стартап Россия 2026",
            "конкурс IT стартап грант ФАСИ Сколково 2026",
            "тендер разработка ИИ автоматизация 2026",
            # Научные гранты и конкурсы
            "научный грант Россия 2026 приём заявок",
            "грант IT исследование НИОКР 2026",
            "РНФ РФФИ конкурс грант 2026 открыт",
            "президентский грант НКО технологии 2026",
            "субсидия безвозмездная разработка ПО Россия 2026",
            # Отраслевые и региональные
            "РФРИТ грант разработка отечественное ПО 2026",
            "социальный контракт открытие бизнеса IT 2026",
            "гранты.рф конкурсы приём заявок 2026",
            "Росмолодёжь грант IT проект 2026",
        ]

        results: list[Opportunity] = []

        async with httpx.AsyncClient(timeout=10.0) as client:
            for q in queries:
                try:
                    found = await self._search_query(client, q)
                    results.extend(found)
                except Exception as exc:
                    logger.warning("Search failed for %r: %s", q, exc)

        seen_urls: set[str] = set()
        unique: list[Opportunity] = []
        for opp in results:
            if opp.url in seen_urls:
                continue
            # Фильтруем новостные статьи
            if any(s in opp.url.lower() for s in self._ARTICLE_DOMAINS):
                continue
            # Фильтруем по прошедшим датам (дедлайн < сегодня)
            if self._is_expired(opp):
                continue
            # Фильтруем конкурсы, на которые участник не может подать
            if self._is_ineligible(opp):
                continue
            seen_urls.add(opp.url)
            unique.append(opp)

        for opp in unique:
            opp.relevance_score = self._calc_relevance(opp)

        unique.sort(key=lambda x: x.relevance_score, reverse=True)
        self._found = unique
        return self._found

    # ─── 2. Глубокий анализ конкурса ────────────────────────────────────────

    async def _fetch_page_text(self, url: str) -> str:
        """Загрузить текст страницы по URL (для анализа документации конкурса)."""
        try:
            async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code != 200:
                    return ""
                html = resp.text
                # Убираем скрипты, стили, теги — оставляем текст
                import re as _re
                html = _re.sub(r"<script[^>]*>.*?</script>", "", html, flags=_re.DOTALL)
                html = _re.sub(r"<style[^>]*>.*?</style>", "", html, flags=_re.DOTALL)
                html = _re.sub(r"<[^>]+>", " ", html)
                html = _re.sub(r"\s+", " ", html)
                return html.strip()[:8000]
        except Exception as exc:
            logger.warning("Failed to fetch %s: %s", url, exc)
            return ""

    _ARTICLE_DOMAINS = [
        "tadviser", "habr", "vc.ru", "rbc.ru", "kommersant",
        "vedomosti", "forbes", "cnews", "comnews", "wiki",
        "spark-interfax", "youtube", "t.me", "vk.com",
        "productradar", "product-radar", "rb.ru", "incrussia",
        "banki.ru", "sravni.ru",
    ]

    async def _gather_official_docs(self, title: str, url: str) -> list[tuple[str, str]]:
        """Ищет официальные страницы конкурса и загружает их содержимое.
        Возвращает список (url, text) с официальных сайтов."""
        pages: list[tuple[str, str]] = []

        # 1. Пробуем исходный URL (если не статья)
        is_article = any(s in url.lower() for s in self._ARTICLE_DOMAINS)
        if not is_article:
            text = await self._fetch_page_text(url)
            if len(text) > 200:
                pages.append((url, text))

        # 2. Извлекаем короткое название для поиска
        short_title = title[:80]

        # 3. Поиск официальных страниц — до 3 страниц (для скорости)
        search_queries = [
            f"{short_title} официальный сайт подача заявки",
            f"{short_title} положение условия участия требования",
            f"{short_title} site:fasie.ru OR site:rscf.ru OR site:sk.ru OR site:рфрит.рф",
        ]

        seen_urls = {url}
        async with httpx.AsyncClient(timeout=8.0) as client:
            for q in search_queries:
                if len(pages) >= 3:
                    break
                try:
                    results = await self._search_query(client, q)
                    for r in results[:5]:
                        if r.url in seen_urls:
                            continue
                        seen_urls.add(r.url)
                        if any(s in r.url.lower() for s in self._ARTICLE_DOMAINS):
                            continue
                        text = await self._fetch_page_text(r.url)
                        if len(text) > 300:
                            pages.append((r.url, text))
                            if len(pages) >= 3:
                                break
                except Exception as exc:
                    logger.warning("Official docs search failed for %r: %s", q, exc)

        return pages

    async def deep_analyze(self, title: str, url: str, description: str = "",
                           custom_urls: list[str] | None = None) -> str:
        """Полный анализ конкурса: правила, требования, отчётность, сроки.
        custom_urls — список URL, предоставленных пользователем для анализа."""
        pages: list[tuple[str, str]] = []

        # Если пользователь дал свои ссылки — используем их
        if custom_urls:
            for cu in custom_urls:
                text = await self._fetch_page_text(cu)
                if len(text) > 100:
                    pages.append((cu, text))

        # Если ссылок нет или они не загрузились — ищем автоматически
        if not pages:
            pages = await self._gather_official_docs(title, url)

        if not pages:
            return "Не удалось загрузить страницу конкурса. Попробуй другой."

        parts = []
        for page_url, page_text in pages:
            parts.append(f"--- {page_url} ---\n{page_text[:3000]}")
        docs_context = "\n\n".join(parts)

        prompt = f"""Проанализируй конкурс/грант на основе документации.

КОНКУРС: {title}
ОПИСАНИЕ: {description}

ДОКУМЕНТАЦИЯ:
{docs_context}

{PARTICIPANT_CONTEXT}

ПРАВИЛА:
- Анализируй на основе фактов из документации.
- НЕ пиши что данных нет, не пиши что документация неполная.
- Если параметр не найден — просто пропусти его.
- Давай только конкретику: цифры, даты, требования.
- НЕ пиши инструкции что делать пользователю (перейти на сайт, скачать положение и т.д.) — ты сам уже это сделал.
- НЕ пиши "что нужно сделать", "перейдите", "скачайте", "проверьте" — только готовый результат анализа.

Формат КРАТКО:

## Суть
Тип | Сумма | Дедлайн | Срок реализации

## Чеклист требований
✅ — участник соответствует
❌ — не соответствует (укажи что нужно: ООО с ценой, научрук с требованиями, публикации и т.д.)

## Деньги
Безвозмездно/возвратно | Что покрывает | Софинансирование

## Вердикт
1 строка: подавать или нет и почему."""
        return await self._call_llm(prompt, max_tokens=4000)

    # ─── 3. Генерация идей ПОД КОНКРЕТНЫЙ конкурс ───────────────────────────

    async def generate_ideas_for_grant(self, grant_title: str, grant_analysis: str) -> str:
        """Генерация идей именно для этого конкурса — быстрая реализация, мин. риски."""
        prompt = f"""Сгенерируй 5 идей проектов для подачи на конкурс.

КОНКУРС: {grant_title}

АНАЛИЗ КОНКУРСА:
{grant_analysis[:3000]}

{PARTICIPANT_CONTEXT}

ВАЖНО:
- Идеи НЕ должны быть привязаны к конкретному бизнесу участника
- Цель: получить безвозмездные деньги и престиж с минимумом ресурсов
- Собственные средства: 0 руб, только грантовые
- Участник умеет программировать и работать с AI/ML

Формат КРАТКО:

## Идея [N]: [Название]
- Суть: 1-2 предложения
- Почему подходит под конкурс: 1 предложение
- Срок MVP: дней/недель
- Что нужно привлечь:
  ✅ / ❌ по каждому ресурсу (люди, организация, документы)
- Сколько денег принесёт и какой престиж"""
        return await self._call_llm(prompt, max_tokens=4000, temperature=0.6)

    # ─── 4. Генерация Excel-калькуляции ─────────────────────────────────────

    async def generate_budget_json(self, idea_title: str, grant_amount: str, duration: str) -> str:
        """Генерация структуры бюджета в JSON для последующей конвертации в Excel."""
        prompt = f"""Составь детальную смету проекта для грантовой заявки.

ПРОЕКТ: {idea_title}
СУММА ГРАНТА: {grant_amount}
СРОК РЕАЛИЗАЦИИ: {duration}

{PARTICIPANT_CONTEXT}

Ответь СТРОГО в JSON формате (без markdown):
{{
  "project_title": "название",
  "total_budget": 0,
  "grant_amount": 0,
  "own_funds": 0,
  "duration_months": 0,
  "categories": [
    {{
      "name": "ФОТ (фонд оплаты труда)",
      "items": [
        {{"name": "Руководитель проекта", "unit": "мес", "quantity": 6, "price": 50000, "total": 300000}},
        {{"name": "Разработчик AI/ML", "unit": "мес", "quantity": 6, "price": 80000, "total": 480000}}
      ],
      "subtotal": 780000
    }},
    {{
      "name": "Инфраструктура",
      "items": [
        {{"name": "Облачный сервер (Hetzner)", "unit": "мес", "quantity": 6, "price": 5000, "total": 30000}},
        {{"name": "API Claude (Anthropic)", "unit": "мес", "quantity": 6, "price": 10000, "total": 60000}}
      ],
      "subtotal": 90000
    }},
    {{
      "name": "Прочие расходы",
      "items": [...],
      "subtotal": 0
    }}
  ],
  "timeline": [
    {{"stage": "Этап 1: MVP", "months": "1-2", "deliverables": ["MVP платформы"], "budget": 0}},
    {{"stage": "Этап 2: Тестирование", "months": "3-4", "deliverables": ["Пилот"], "budget": 0}}
  ]
}}

Правила:
- Смету считать близко к верхнему порогу гранта
- ФОТ максимальный в рамках разумного
- Учесть налоги на ФОТ (страховые взносы ~30% или 7.6% для IT)
- Все суммы в рублях
- Итого должно равняться сумме гранта"""
        return await self._call_llm(prompt, max_tokens=3000, temperature=0.2)

    # ─── 5. Генерация документов на подачу ──────────────────────────────────

    async def generate_submission_docs(self, idea_title: str, idea_description: str,
                                        grant_title: str, budget_json: str = "") -> str:
        """Генерация пакета документов для подачи заявки."""
        prompt = f"""Подготовь пакет документов для подачи заявки на грант/конкурс.

КОНКУРС: {grant_title}
ПРОЕКТ: {idea_title}
ОПИСАНИЕ: {idea_description}
БЮДЖЕТ: {budget_json[:2000] if budget_json else 'не указан'}

{PARTICIPANT_CONTEXT}

Подготовь следующие документы:

## 1. ЗАЯВКА (аннотация проекта)
- Название проекта
- Аннотация (до 500 слов)
- Актуальность и проблема
- Цель и задачи
- Научная/техническая новизна
- Ожидаемые результаты
- Практическая значимость

## 2. ТЕХНИЧЕСКОЕ ЗАДАНИЕ
- Описание текущего состояния
- Требования к результату
- Этапы выполнения
- Критерии приёмки

## 3. ПЛАН РАБОТ
- Этапы с датами и ответственными
- Контрольные точки (milestones)
- Риски и митигация

## 4. ОБОСНОВАНИЕ БЮДЖЕТА
- По каждой статье: зачем нужно, почему такая сумма

## 5. ЧЕК-ЛИСТ ПОДАЧИ
- Все документы для прикрепления
- Форматы и требования
- Кто подписывает"""
        return await self._call_llm(prompt, max_tokens=4000)

    # ─── 6. Генерация общих идей ────────────────────────────────────────────

    async def generate_ideas(self, context: str = "") -> str:
        """Генерация идей заработка (общая, без привязки к конкурсу)."""
        prompt = f"""Ты — стратегический советник IT-стартапа AI Zavod.

{PARTICIPANT_CONTEXT}

{f'ДОПОЛНИТЕЛЬНЫЙ КОНТЕКСТ: {context}' if context else ''}

СГЕНЕРИРУЙ 10 КОНКРЕТНЫХ ИДЕЙ для заработка, отсортированных по:
- Скорость получения денег (дни, не месяцы)
- Минимальные вложения
- Использование уже готовых модулей

Формат каждой идеи:
## [Номер]. [Название]
- **Что:** конкретное описание
- **Кому продать:** целевой клиент
- **Сколько:** ожидаемый доход
- **Срок:** время до первых денег
- **Как начать:** 3 конкретных шага"""
        return await self._call_llm(prompt, temperature=0.7)

    # ─── 7. Сводка источников ───────────────────────────────────────────────

    async def scan_sources_summary(self) -> str:
        """Форматированная сводка всех известных источников."""
        lines = ["<b>Источники возможностей для AI Zavod:</b>\n"]
        by_type: dict[str, list[dict]] = {}
        for s in SOURCES:
            by_type.setdefault(s["type"], []).append(s)

        type_labels = {
            "grant": "Гранты",
            "hackathon": "Хакатоны",
            "competition": "Конкурсы/Соревнования",
            "accelerator": "Акселераторы",
        }

        for t, label in type_labels.items():
            sources = by_type.get(t, [])
            if not sources:
                continue
            lines.append(f"\n<b>{label}:</b>")
            for s in sources:
                lines.append(f"• <b>{s['name']}</b> — {s['programs']}")

        return "\n".join(lines)

    # ─── 8. Анализ отдельной возможности ────────────────────────────────────

    async def analyze_opportunity(self, opp: Opportunity) -> str:
        """Быстрый анализ найденной возможности."""
        prompt = f"""Проанализируй эту возможность для AI Zavod:

ВОЗМОЖНОСТЬ:
- Название: {opp.title}
- Тип: {opp.type}
- Источник: {opp.source}
- Дедлайн: {opp.deadline or 'не указан'}
- Приз/сумма: {opp.prize or 'не указано'}
- Описание: {opp.description}

{PARTICIPANT_CONTEXT}

ОТВЕТЬ КРАТКО:
1. Подходит ли нам? (да/нет/частично) и почему
2. Что подать/показать
3. Шансы на победу (низкие/средние/высокие)
4. Конкретные шаги (3-5 пунктов)
5. Потенциальный выигрыш"""
        result = await self._call_llm(prompt, max_tokens=1500)
        opp.ai_analysis = result
        return result

    # ─── Internals ──────────────────────────────────────────────────────────

    async def _search_query(
        self, client: httpx.AsyncClient, query: str
    ) -> list[Opportunity]:
        url = "https://html.duckduckgo.com/html/"
        try:
            resp = await client.post(url, data={"q": query}, headers={
                "User-Agent": "Mozilla/5.0 (compatible; AIZavod/1.0)"
            })
            if resp.status_code != 200:
                return []
            return self._parse_ddg_results(resp.text, query)
        except Exception as exc:
            logger.warning("DuckDuckGo search failed: %s", exc)
            return []

    def _parse_ddg_results(self, html: str, query: str) -> list[Opportunity]:
        results: list[Opportunity] = []
        link_pattern = re.compile(
            r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', re.DOTALL
        )
        snippet_pattern = re.compile(
            r'class="result__snippet"[^>]*>(.*?)</[^>]+>', re.DOTALL
        )
        links = link_pattern.findall(html)
        snippets = snippet_pattern.findall(html)

        for i, (url, title) in enumerate(links[:10]):
            from html import unescape
            title = unescape(re.sub(r"<[^>]+>", "", title)).strip()
            snippet = ""
            if i < len(snippets):
                snippet = unescape(re.sub(r"<[^>]+>", "", snippets[i])).strip()

            if "uddg=" in url:
                match = re.search(r"uddg=([^&]+)", url)
                if match:
                    from urllib.parse import unquote
                    url = unquote(match.group(1))

            opp_type = "grant"
            for kw, t in [("хакатон", "hackathon"), ("hackathon", "hackathon"),
                          ("конкурс", "competition"), ("contest", "competition"),
                          ("акселератор", "accelerator"), ("тендер", "tender")]:
                if kw in title.lower() or kw in snippet.lower():
                    opp_type = t
                    break

            results.append(Opportunity(
                title=title, source="DuckDuckGo", url=url,
                type=opp_type, description=snippet,
            ))
        return results

    @staticmethod
    def _is_expired(opp: Opportunity) -> bool:
        """Проверяет, истёк ли дедлайн (ищет даты в заголовке и описании)."""
        from datetime import timedelta
        today = datetime.utcnow().date()
        min_date = today + timedelta(days=1)  # минимум 1 день до дедлайна
        text = f"{opp.title} {opp.description}"

        # Ищем даты вида DD.MM.YYYY или DD/MM/YYYY
        date_patterns = re.findall(r"(\d{1,2})[./](\d{1,2})[./](20\d{2})", text)
        for day, month, year in date_patterns:
            try:
                d = datetime(int(year), int(month), int(day)).date()
                # Если найденная дата похожа на дедлайн и она в прошлом
                if d < min_date:
                    return True
            except ValueError:
                continue

        # Ищем даты вида "до 15 октября 2025"
        months_ru = {
            "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
            "мая": 5, "июня": 6, "июля": 7, "августа": 8,
            "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
        }
        ru_dates = re.findall(r"(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(20\d{2})", text.lower())
        for day, month_name, year in ru_dates:
            try:
                d = datetime(int(year), months_ru[month_name], int(day)).date()
                if d < min_date:
                    return True
            except (ValueError, KeyError):
                continue

        return False

    # Конкурсы, где участник точно не может подать заявку лично
    _INELIGIBLE_KEYWORDS = [
        "студенческий стартап", "только для студентов",
        "студенческий конкурс", "школьник", "для школьников",
        "только нко",
        "scholarship", "student only",
    ]

    @staticmethod
    def _is_ineligible(opp: Opportunity) -> bool:
        """Фильтрует конкурсы, где участник точно не может участвовать.
        Вузовские гранты проходят — можно участвовать как исполнитель по ГПХ."""
        text = f"{opp.title} {opp.description}".lower()
        for kw in OpportunityScanner._INELIGIBLE_KEYWORDS:
            if kw in text:
                return True
        return False

    def _calc_relevance(self, opp: Opportunity) -> float:
        text = f"{opp.title} {opp.description}".lower()
        matches = sum(1 for kw in RELEVANCE_KEYWORDS if kw.lower() in text)
        return min(matches / 5.0, 1.0)


# Singleton
_scanner: OpportunityScanner | None = None


def get_scanner() -> OpportunityScanner:
    global _scanner
    if _scanner is None:
        _scanner = OpportunityScanner()
    return _scanner
