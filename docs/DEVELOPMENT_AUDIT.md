# DEVELOPMENT AUDIT: Zavod-ii Platform

## Аудит плана разработки + Методы военной промышленности для AI-агентной системы

**Дата:** 2026-03-20
**Версия:** 1.0
**Стандарты:** 8 РФ (ГОСТ РВ / ГОСТ Р) + 5 западных (MIL-STD / DO-178C)

---

# ЧАСТЬ 1: Матрица плана разработки AI-агентного продукта

## Сводка

| Категория | Всего | ЕСТЬ | ЧАСТИЧНО | НЕТ |
|-----------|-------|------|----------|-----|
| Фаза 0: Исследование | 4 | 2 | 2 | 0 |
| Фаза 1: Архитектура | 7 | 4 | 0 | 3 |
| Фаза 2: MVP | 12 | 8 | 4 | 0 |
| Фаза 3: Тестирование | 8 | 1 | 4 | 3 |
| Фаза 4: Продакшен | 15 | 5 | 3 | 7 |
| Фаза 5: Масштабирование | 9 | 0 | 0 | 9 |
| **ИТОГО** | **55** | **20 (36%)** | **13 (24%)** | **22 (40%)** |

**Блокеры P0: 7 пунктов** | **P1: 16 пунктов** | **P2: 8 пунктов**

---

## ФАЗА 0: Исследование и валидация

| # | Пункт | Статус | Файл/Доказательство | P |
|---|-------|--------|---------------------|---|
| 0.1 | Анализ рынка (7 конкурентов, $10.9B) | ЕСТЬ | PROBLEMS_SOLUTIONS.md | — |
| 0.2 | Custdev (1 persona, нет интервью) | ЧАСТИЧНО | RULES_MASTER.md | P1 |
| 0.3 | Финмодель (нет LTV/CAC/payback) | ЧАСТИЧНО | observability.py, metering.py | P1 |
| 0.4 | Use-case selection (CERTIFIER, 291 ОКВЭД) | ЕСТЬ | registry.py | — |

## ФАЗА 1: Архитектура

| # | Пункт | Статус | Файл | P |
|---|-------|--------|------|---|
| 1.1 | Hierarchical orchestration | ЕСТЬ | hierarchy.py (9 директоров) | — |
| 1.2 | 3-tier (Knowledge/Reasoning/Action) | ЕСТЬ | memory.py / llm_client.py / routes.py | — |
| 1.3 | Модульная структура агента | ЕСТЬ | schemas.py (AgentInfo, AgentMessage) | — |
| 1.4 | Стек определён | ЕСТЬ | docker-compose.yml, requirements.txt | — |
| 1.5 | Протоколы MCP/A2A | НЕТ | Заложено ENTERPRISE 2027+ | P2 |
| 1.6 | Диаграммы C4/ADR | НЕТ | Текст в CLAUDE.md | P1 |
| 1.7 | Event-driven bus | НЕТ | Celery есть, не event bus | P2 |

## ФАЗА 2: MVP

| # | Пункт | Статус | Файл | P |
|---|-------|--------|------|---|
| 2.1 | 21+ агентов | ЕСТЬ | registry.py | — |
| 2.2 | Оркестратор (router + orchestrator) | ЕСТЬ | core.py | — |
| 2.3 | Task Decomposition 3-level | ЕСТЬ | orchestrate() + prompts | — |
| 2.4 | Agent Registry | ЕСТЬ | registry.py | — |
| 2.5 | State Manager | ЕСТЬ | models.py (ConductorTask) | — |
| 2.6 | Память Letta 3-level | ЕСТЬ | memory.py | — |
| 2.7 | RAG (только BM25, нет vectors) | ЧАСТИЧНО | agentic_rag.py | P1 |
| 2.8 | Интеграции | ЕСТЬ | Telegram, Claude, Ollama, n8n | — |
| 2.9 | UI Dashboard | ЧАСТИЧНО | web-ui/dist/ (нет src) | P1 |
| 2.10 | Human-in-the-loop | ЕСТЬ | compliance_agent.py | — |
| 2.11 | Параллельный dispatch | ЧАСТИЧНО | safeguards.py (не интегрирован) | P1 |
| 2.12 | Progress streaming | ЧАСТИЧНО | UXTransparency (не в UI) | P1 |

## ФАЗА 3: Тестирование и оптимизация

| # | Пункт | Статус | Файл | P |
|---|-------|--------|------|---|
| 3.1 | Evaluation framework | НЕТ | Нет golden set, нет RAGAS | **P0** |
| 3.2 | Unit tests (5/21 агентов) | ЧАСТИЧНО | tests/unit/ | P1 |
| 3.3 | Integration tests (2) | ЧАСТИЧНО | tests/integration/ | P1 |
| 3.4 | Adversarial tests (1) | ЧАСТИЧНО | tests/adversarial/ | P1 |
| 3.5 | Load tests | НЕТ | — | P1 |
| 3.6 | Cost optimization | ЕСТЬ | llm_client.py (caching 90%) | — |
| 3.7 | Security audit | ЧАСТИЧНО | OWASP checklist, нет pentest | P1 |
| 3.8 | Coverage metric | НЕТ | Нет pytest-cov | P1 |

## ФАЗА 4: Продакшен-деплой

| # | Пункт | Статус | Файл | P |
|---|-------|--------|------|---|
| 4.1 | Docker Compose (8 контейнеров) | ЕСТЬ | docker-compose.yml | — |
| 4.2 | CI/CD | ЕСТЬ | .github/workflows/deploy.yml | — |
| 4.3 | Observability | ЕСТЬ | observability.py, session_trace.py | — |
| 4.4 | Governance & Guardrails | ЕСТЬ | safeguards.py (10 классов) | — |
| 4.5 | Kill switch (DEADMAN) | ЕСТЬ | health_monitor.py | — |
| 4.6 | Health endpoint (нет dep checks) | ЧАСТИЧНО | /health = {"status":"ok"} | **P0** |
| 4.7 | Canary / Feature flags | НЕТ | ab_engine.py не интегрирован | **P0** |
| 4.8 | Centralized logging | ЧАСТИЧНО | RotatingFileHandler, нет JSON | **P0** |
| 4.9 | Backup / DR | НЕТ | Нет pg_dump, нет RTO/RPO | **P0** |
| 4.10 | Secrets management | НЕТ | Всё в .env, хардкод в compose | **P0** |
| 4.11 | Rate limiting middleware | НЕТ | Metering без блокировки | P1 |
| 4.12 | Monitoring (Prometheus/Grafana) | НЕТ | Только in-memory | P1 |
| 4.13 | Alerting | НЕТ | cost alerts, не внешние | P1 |
| 4.14 | Database replication | НЕТ | Single-node | P2 |
| 4.15 | Horizontal scaling | НЕТ | Docker Compose = 1 сервер | P2 |

## ФАЗА 5: Масштабирование

| # | Пункт | Статус | P |
|---|-------|--------|---|
| 5.1 | Multi-tenancy | НЕТ (нет tenant_id) | **P0** |
| 5.2 | User auth (JWT/OAuth) | НЕТ | P1 |
| 5.3 | Payment (YooKassa) | НЕТ | P1 |
| 5.4 | Marketplace агентов | НЕТ | P2 |
| 5.5 | Developer SDK/API docs | НЕТ | P2 |
| 5.6 | API versioning (/api/v1/) | НЕТ | P1 |
| 5.7 | White-label | НЕТ | P2 |
| 5.8 | SLA monitoring | НЕТ | P2 |
| 5.9 | Plugin система | НЕТ | P2 |

---

# ЧАСТЬ 2: Военные стандарты для AI-агентной системы

## 13 стандартов: 8 российских + 5 западных

### Западные (NATO / US / EASA)

| Стандарт | Область | Что берём для Zavod-ii |
|----------|---------|------------------------|
| **MIL-STD-498** | Разработка и документация ПО (22 DID) | RTM, 6 типов документов, Review Gates |
| **DO-178C** | Safety-critical ПО, 5 DAL levels | V&V gate, structural coverage, independence |
| **MIL-STD-882E** | Системная безопасность | Hazard Analysis, Safety Cases |
| **MIL-STD-1629A** | Анализ отказов FMEA/FMECA | S×O×D=RPN для каждого агента |
| **MIL-HDBK-338B** | Надёжность и отказоустойчивость | Redundancy, fault tolerance |

### Российские военные стандарты (ГОСТ РВ / ГОСТ Р)

| Стандарт | Область | Что берём для Zavod-ii |
|----------|---------|------------------------|
| **ГОСТ РВ 0015-002-2020** | СМК военной продукции (ISO 9001 + доп.) | Управление конфигурацией, аудиты, lifecycle |
| **ГОСТ РВ 0015-003-2024** | Проверка СМК (01.01.2025) | Trigger-based аудиты, компетенции проверяющих |
| **ГОСТ Р 51904-2002** | ПО встроенных систем (аналог DO-178B) | 5 уровней критичности, MC/DC покрытие |
| **ГОСТ 27.310-95 / Р 27.303-2021** | FMEA/FMECA (аналог MIL-STD-1629A) | S×O×D=RPN по ГОСТ формату |
| **ГОСТ Р 56939-2024** | Безопасная разработка ПО (20.12.2024) | Secure coding, V&V, управление рисками |
| **ГОСТ 19.101-2024** (ЕСПД) | 14 типов программных документов (30.01.2025) | 6 документов для Zavod-ii |
| **ГОСТ Р 56920-2024** | Тестирование ПО | Уровни и методы тестирования |
| **ГОСТ Р 59194-2020** | Управление требованиями | Прослеживаемость, baseline, change mgmt |

---

## Детальный разбор ГОСТ РВ 0015-002-2020

### Структура (11 разделов)

1. Область применения
2. Нормативные ссылки
3. Термины и определения
4. **Среда организации** — контекст, заинтересованные стороны, scope СМК
5. **Лидерство** — ответственность руководства, политика качества
6. **Планирование** — управление рисками и возможностями, цели качества
7. **Среда обеспечения** — ресурсы, компетенции, документированная информация
8. **Деятельность на стадиях ЖЦ** — планирование, требования, проектирование, закупки, производство, выпуск, управление несоответствиями
9. **Оценка результатов** — мониторинг, внутренние аудиты, анализ руководства
10. **Улучшение** — корректирующие действия, постоянное улучшение
11. **Требования к режиму секретности**

### 10 ключевых требований

1. Стандарты качества на ВСЕХ стадиях разработки и производства
2. СМК с контролем и улучшением качества продукции
3. Формальные требования к документации
4. Систематический контроль и аудиты процессов
5. Обязательное непрерывное улучшение
6. Соответствие законодательству РФ
7. Обеспечение безопасности пользователей и среды
8. Регулированные отношения с поставщиками
9. Требования к обучению персонала
10. Сертификация соответствия

### Новшества 2020 vs 2012

- **Управление конфигурацией** — выделено в отдельное требование
- Ужесточение документации, контроля, аудитов
- Обязательная оценка и мониторинг рисков
- Процедуры управления несоответствиями

### Маппинг на Zavod-ii

| Раздел ГОСТ | Что берём | Файл в проекте |
|-------------|-----------|----------------|
| 6. Планирование рисков | Hazard Analysis | docs/HAZARD_ANALYSIS.yaml |
| 8. Деятельность на стадиях ЖЦ | RTM + lifecycle tracking | docs/RTM.yaml + safeguards.py |
| 9. Аудиты | Автоматические review gates | scripts/release_gate.py |
| Управление конфигурацией | Baseline management | configs/baseline.yaml |

---

## Детальный разбор ГОСТ РВ 0015-003-2024 (вступил 01.01.2025)

### Ключевые новшества

- Расширены основания для **внеплановых проверок**: проблемы качества, оценка выполнимости, нарушения
- **Минимальный набор** документированной информации для анализа при проверках
- Формальные **требования к компетенциям** проверяющих (criteria-based)
- Расширена роль МО РФ в надзоре

### Маппинг на Zavod-ii

| Требование ГОСТ | Наша реализация | Файл |
|-----------------|-----------------|------|
| Trigger-based аудиты | DARWIN score < 3 или error_rate > 30% → аудит | safeguards.py (LifecycleManager) |
| Минимальный набор данных | Session replay + ErrorTracker blame | session_trace.py |
| Компетенции проверяющих | QA-AGENT с формализованными критериями | qa_agent.py |

---

## Детальный разбор ГОСТ Р 51904-2002 (аналог DO-178B)

### 5 уровней критичности ПО

| Уровень | Последствия отказа | Требования к покрытию |
|---------|--------------------|-----------------------|
| A | Катастрофический | MC/DC + 100% structural coverage |
| B | Опасный | Decision coverage + 100% |
| C | Существенный | Statement coverage + testing |
| D | Незначительный | Basic testing |
| E | Без последствий | Нет требований |

### MC/DC (Modified Condition/Decision Coverage)

- Каждая точка входа/выхода вызвана минимум 1 раз
- Каждое условие проверено со ВСЕМИ возможными результатами
- Верификация = оценка корректности и непротиворечивости
- Валидация = подтверждение соответствия назначению

### Присвоение уровней агентам Zavod-ii

| Уровень | Агенты | Обоснование | Требования |
|---------|--------|-------------|------------|
| C (Существенный) | CERTIFIER, LAWYER, ACCOUNTANT | Юр./фин. последствия ошибок | QA eval + golden tests + human approval |
| D (Незначительный) | PRICING, OUTREACH, CONTENT, NAMER, HERALD, MARKET | Бизнес-последствия | QA quick_check |
| E (Без последствий) | IDEA_GENERATOR, SCHOLAR, VOICE | Информационный характер | Базовый QA |

---

## Детальный разбор ГОСТ 27.310-95 / ГОСТ Р 27.303-2021 (FMEA)

### Методология FMEA по ГОСТ

- Систематическое выявление возможных отказов каждого компонента
- **RPN = Severity (S) × Occurrence (O) × Detection (D)**
- S, O, D оцениваются по шкале 1-10
- Для критичных элементов: резервирование, перестраиваемая структура
- Цель: поддержка решений по снижению вероятности отказов

### Пример FMEA для CONDUCTOR

| Компонент | Failure Mode | S | O | D | RPN | Mitigation |
|-----------|-------------|---|---|---|-----|------------|
| LLM Client | API timeout | 7 | 4 | 2 | 56 | CircuitBreaker → Ollama fallback |
| LLM Client | Hallucination | 8 | 5 | 3 | 120 | QA-AGENT + DARWIN + extended thinking |
| Router | Неправильная маршрутизация | 6 | 3 | 3 | 54 | Keyword + LLM двойная классификация |
| QA-AGENT | Пропуск PII | 9 | 2 | 4 | 72 | Regex + LLM double-check |
| CERTIFIER | Ошибочный юр. совет | 9 | 3 | 5 | 135 | Human approval gate + disclaimer |
| LAWYER | Неправильная ссылка на закон | 9 | 4 | 4 | 144 | RAG verification + QA + disclaimer |
| Inter-agent | Prompt injection chain | 8 | 2 | 3 | 48 | InterAgentFirewall + sanitize |
| Orchestrator | Deadlock | 7 | 2 | 2 | 28 | DeadlockDetector (DFS) |
| Health | Agent unresponsive | 5 | 3 | 2 | 30 | DEADMAN kill-switch + auto-revive |
| Billing | Перерасход токенов | 6 | 4 | 2 | 48 | Metering limits + cost alerts |

**RPN > 100 (требуют усиленного контроля):**
- CERTIFIER (135) — **решено:** approval gates + AI disclaimer
- LAWYER (144) — **решено:** RAG + QA + disclaimer
- Hallucination (120) — **решено:** QA-AGENT + DARWIN + extended thinking

---

## Детальный разбор ГОСТ Р 56939-2024 (введён 20.12.2024)

### Требования к безопасной разработке ПО

| Требование | Статус в Zavod-ii | Файл |
|------------|-------------------|------|
| Критерии безопасности кода | ЕСТЬ | InterAgentFirewall, PermissionGuard (safeguards.py) |
| Верификация | ЕСТЬ | QA-AGENT (qa_agent.py) + DARWIN |
| Валидация | ЧАСТИЧНО | Golden tests (tests/golden/), нужно расширить |
| Управление рисками | ЕСТЬ | HAZARD_ANALYSIS + FMEA + ErrorTracker |
| Тестирование компонентов | ЧАСТИЧНО | 74 теста, нужно расширить до всех агентов |
| Документирование | ЧАСТИЧНО | CLAUDE.md, PROBLEMS_SOLUTIONS.md, нужны RTM + ARCHITECTURE |

---

## Детальный разбор ГОСТ 19.101-2024 (ЕСПД, введён 30.01.2025)

### 14 типов документов по ЕСПД

1. Спецификация
2. Ведомость держателей подлинников
3. Текст программы
4. Описание программы
5. Программа и методика испытаний
6. Техническое задание
7. Пояснительная записка
8. Эксплуатационные документы
9. Руководство системного программиста
10. Руководство программиста
11. Руководство оператора
12. Описание языка
13. Ведомость эксплуатационных документов
14. Формуляр

### 6 документов для Zavod-ii (кросс-маппинг)

| ЕСПД | MIL-STD-498 | Наш файл | Статус |
|------|-------------|----------|--------|
| Техническое задание | SRS | docs/RTM.yaml | Создать |
| Описание программы | SDD | docs/ARCHITECTURE.md | Создать |
| Программа и методика испытаний | STP | docs/TEST_PLAN.md | Создать |
| Руководство оператора | OCD | docs/OPERATIONS.md | Создать |
| Руководство программиста | SUM | docs/USER_GUIDE.md | Создать |
| Пояснительная записка | — | docs/PROBLEMS_SOLUTIONS.md | ЕСТЬ |

---

# ЧАСТЬ 3: 10 методов военной промышленности для внедрения

## Метод 1: Requirements Traceability Matrix (RTM)
**Стандарт:** MIL-STD-498 + ГОСТ Р 59194-2020
**Суть:** Каждое требование → код → тест → результат. Ничего не теряется.
**Файлы:** `docs/RTM.yaml`, `scripts/check_rtm.py`
**CI:** check_rtm.py блокирует deploy при coverage < 80%

## Метод 2: FMEA per Agent
**Стандарт:** MIL-STD-1629A + ГОСТ 27.310-95
**Суть:** S×O×D=RPN для каждого агента. RPN > 100 → fallback + автотест.
**Файлы:** `docs/FMEA.yaml`, safeguards.py (расширить ErrorTracker)

## Метод 3: Independent V&V Gate
**Стандарт:** DO-178C + ГОСТ Р 51904-2002
**Суть:** QA-AGENT = mandatory gate. DARWIN = independent validator. Кто писал != кто тестирует.
**Файлы:** core.py (mandatory gate), tests/golden/ (50+ examples)

## Метод 4: Configuration Management & Baselines
**Стандарт:** DO-178C + ГОСТ РВ 0015-002-2020
**Суть:** Фиксация промптов/моделей/конфигов в production. Мгновенный rollback.
**Файлы:** `configs/baseline.yaml`, `scripts/rollback_to_baseline.py`

## Метод 5: Hazard Analysis
**Стандарт:** MIL-STD-882E + ГОСТ РВ 0015-002-2020 (раздел 6)
**Суть:** 10 формальных опасностей с severity/likelihood/risk_level.
**Файлы:** `docs/HAZARD_ANALYSIS.yaml`, tests/adversarial/ (расширить)

## Метод 6: Review Gates
**Стандарт:** MIL-STD-498 + ГОСТ РВ 0015-003-2024
**Суть:** Перед deploy: все тесты OK, RTM > 80%, FMEA без P0.
**Файлы:** `.github/workflows/deploy.yml`, `scripts/release_gate.py`

## Метод 7: Structured Test Pyramid (5 уровней)
**Стандарт:** DO-178C + ГОСТ Р 56920-2024 + ГОСТ РВ 15.307
**Уровни:** L1 Unit → L2 Integration → L3 E2E → L4 Adversarial → L5 Regression

## Метод 8: Redundancy & Fault Tolerance
**Стандарт:** MIL-HDBK-338B + ГОСТ 27.310-95
**Суть:** Health check зависимостей, degraded mode, /health/ready + /health/live.

## Метод 9: Documentation Discipline
**Стандарт:** MIL-STD-498 (6 из 22 DID) + ГОСТ 19.101-2024 (6 из 14)
**Документы:** RTM, ARCHITECTURE, TEST_PLAN, OPERATIONS, USER_GUIDE, PROBLEMS_SOLUTIONS.

## Метод 10: Formal Audit Trail
**Стандарт:** ГОСТ РВ 0015-002-2020 + ГОСТ РВ 0015-003-2024
**Суть:** ConductorLog + decision_rationale + input/output hash + qa_verdict. Retention 90/365.

---

# ЧАСТЬ 4: Дорожная карта внедрения

## Sprint 1 (Неделя 1): P0 блокеры
1. Health endpoint (PostgreSQL/Redis/LLM check)
2. Secrets management (убрать хардкод из compose)
3. Structured JSON logging
4. Multi-tenancy foundation (tenant_id)
5. Backup strategy (pg_dump daily)

## Sprint 2 (Неделя 2): Военная документация
1. RTM (Метод 1)
2. FMEA для 5 критичных агентов (Метод 2)
3. Hazard Analysis (Метод 5)
4. Architecture docs (Метод 9)

## Sprint 3 (Неделя 3): Тестирование военного уровня
1. Evaluation framework + golden dataset 50+
2. V&V mandatory gate (Метод 3)
3. E2E tests (3 сценария)
4. CI release gate (Метод 6)

## Sprint 4 (Неделя 4): Продуктовые фичи
1. User auth (JWT)
2. Progress streaming (UX → Telegram)
3. Payment (YooKassa)
4. Feature flags (Redis-based)

## Sprint 5 (Неделя 5): Config Management + Operations
1. Baseline management (Метод 4)
2. Operations runbook (Метод 9)
3. Audit trail (Метод 10)
4. Load testing

---

# ЧАСТЬ 5: Сводная матрица — военный метод → пункт плана → стандарт

| Метод | Решает пункты | ГОСТ РФ | MIL-STD/DO | Sprint | P |
|-------|---------------|---------|------------|--------|---|
| RTM | 3.1, 3.8 | ГОСТ Р 59194-2020 | MIL-STD-498 | 2 | P0 |
| FMEA | 4.4, 4.9 | ГОСТ 27.310-95 | MIL-STD-1629A | 2 | P0 |
| V&V Gate | 3.1, 3.7 | ГОСТ Р 51904-2002 | DO-178C | 3 | P0 |
| Config Mgmt | 4.7, 4.10 | ГОСТ РВ 0015-002 | DO-178C | 5 | P1 |
| Hazard Analysis | 4.4, 3.7 | ГОСТ РВ 0015-002 | MIL-STD-882E | 2 | P0 |
| Review Gates | 4.2, 4.7 | ГОСТ РВ 0015-003 | MIL-STD-498 | 3 | P1 |
| Test Pyramid | 3.2-3.5 | ГОСТ Р 56920-2024 | DO-178C | 3 | P0 |
| Redundancy | 4.6, 4.9 | ГОСТ 27.310-95 | MIL-HDBK-338B | 1 | P0 |
| Doc Discipline | 1.6 | ГОСТ 19.101-2024 | MIL-STD-498 | 2,5 | P1 |
| Audit Trail | 4.3, 4.4 | ГОСТ РВ 0015-002 | — | 5 | P1 |

---

## Источники

### Российские стандарты
- [ГОСТ РВ 0015-002-2020 — СМК военной продукции](https://opk.spb.ru/news/gost-rv-0015-002-2020-sistema-razrabotki/)
- [ГОСТ РВ 0015-003-2024 — Проверка СМК (01.01.2025)](https://www.uicc.ru/info/news/gost-rv-0015-003-2024-/)
- [ГОСТ Р 51904-2002 — ПО встроенных систем](http://docs.cntd.ru/document/1200030195/)
- [ГОСТ 27.310-95 — FMEA/FMECA](http://docs.cntd.ru/document/gost-27-310-95)
- [ГОСТ Р 27.303-2021 — FMEA (МЭК 60812:2018)](https://allgosts.ru/03/120/gost_r_27.303-2021)
- [ГОСТ Р 56939-2024 — Безопасная разработка ПО](https://www.consultant.ru/cons/cgi/online.cgi?req=doc&base=OTN&n=42966)
- [ГОСТ 19.101-2024 — ЕСПД виды документов](https://www.rctest.ru/news/opublikovany-gosty-s-trebovaniyami-k-programmnomu-obespecheniyu.html)
- [ГОСТ Р 59194-2020 — Управление требованиями](https://allgosts.ru/35/080/gost_r_59194-2020)

### Западные стандарты
- [MIL-STD-498 — Software Development and Documentation](https://ix23.com/software-development/mil-std-498/)
- [DO-178C — Software Verification](https://www.do178.org/)
- [MIL-STD-882E — System Safety](https://ldra.com/882e/)
- [MIL-STD-1629A — FMECA](https://everyspec.com/MIL-STD/MIL-STD-1600-1699/MIL-STD-1629A_5765/)
