# AI Agent Systems: 25 Problems & Solutions (2025-2026)

## Zavod-ii / AI Zavod — Полный реестр проблем и решений

Дата: 2026-03-19
Версия: 1.0

---

## Часть 1: Проблемы, решённые ДО этого спринта (1-13)

| # | Проблема | Файл решения |
|---|---|---|
| 1 | 95% проектов не доходят до прода | registry.py (291 ОКВЭД), FREE tier |
| 2 | Compounding errors (85%^10=20%) | qa_agent.py (critic pattern) |
| 3 | Dumb RAG | memory.py (Letta 3-level) |
| 4 | Brittle connectors | llm_client.py (CircuitBreaker + Ollama fallback) |
| 5 | Polling tax | conductor_autonomy.py (event-driven) |
| 6 | Token costs x15 | llm_client.py (prompt caching), billing/metering.py |
| 7 | Галлюцинации $67B | qa_agent.py + extended thinking |
| 8 | Security (prompt injection) | qa_agent.py (INJECTION_MARKERS), compliance_agent.py |
| 9 | Статичные системы | darwin_agent.py (self-learning) |
| 10 | Нет governance | observability.py (Langfuse traces), health_monitor.py |
| 11 | Build vs Buy (33% success DIY) | Мы = vendor, PLG, ready-made |
| 12 | Легаси не готово | Telegram-first, zero integration |
| 13 | 152-ФЗ compliance | compliance_agent.py (PII masking, approval gates) |

---

## Часть 2: Новые проблемы, решённые в этом спринте (14-25)

### #14: Silent Deadlock между агентами
**Суть:** Оркестратор ждёт агента A, агент A ждёт B, B ждёт оркестратора. Ошибки нет — бесконечный wait.
**Файл:** `services/conductor/safeguards.py` → `DeadlockDetector`
**Решение:**
- DFS-поиск циклов в графе зависимостей (`detect_cycle()`)
- Pre-execution проверка задач до запуска (`check_dependencies()`)
- Timeout watchdog на каждую пару ожидающих (`detect_timeout_waits()`)
- Интеграция в `core.py` → `orchestrate()` — проверка до декомпозиции

### #15: Latency Cascade
**Суть:** 5 агентов последовательно = 15-30 сек. Пользователь уходит после 5 сек.
**Файл:** `services/conductor/safeguards.py` → `LatencyBudget` + `ParallelDispatcher`
**Решение:**
- Бюджет 10 сек на весь workflow, 5 сек per agent
- Warning при 70% бюджета
- `ParallelDispatcher.find_independent_groups()` — группировка независимых задач
- Topological sort для определения параллельных batch-ей
- Интеграция в `core.py` → `process()` и `orchestrate()`

### #16: Role Confusion (агент выходит за роль)
**Суть:** Pricing-агент утверждает контракты. Lawyer даёт маркетинговые советы.
**Файл:** `services/conductor/safeguards.py` → `RoleBoundaryValidator`
**Решение:**
- `ROLE_BOUNDARIES` dict: per-agent allowed_domains и forbidden_actions
- Regex-based маркеры нарушений (утверждение контрактов, финоперации, удаление данных)
- Post-response проверка в pipeline (`post_response_check()`)
- High severity → error record + logging

### #17: Agent Identity Management
**Суть:** Нет lifecycle, нет credentials per agent, нет audit привязки.
**Файл:** `services/conductor/safeguards.py` → `AgentLifecycle` + `LifecycleManager`
**Решение:**
- 5 состояний: DRAFT → ACTIVE → DEGRADED → SUSPENDED → RETIRED
- Auto-suspend: 30 дней без вызовов
- Auto-retire: 90 дней без вызовов
- Auto-degrade: DARWIN score < 3.0
- Usage tracking: total_calls, unique_users, last_used, avg_darwin_score
- Интеграция: `health_monitor.py` обновлён с SUSPENDED/RETIRED статусами

### #18: Agent-to-Agent Attack (атака через цепочку)
**Суть:** Скомпрометированный агент передаёт вредоносные инструкции дальше.
**Файл:** `services/conductor/safeguards.py` → `InterAgentFirewall`
**Решение:**
- 7 типов injection-паттернов для межагентных сообщений
- `sanitize()` — сканирование + замена опасных паттернов на [SANITIZED]
- `filter_context()` — context isolation: агент получает только нужные поля
- Per-role context access: guardian видит full_response, content_factory — нет

### #19: Agent Sprawl (неконтролируемое размножение)
**Суть:** 21 агент сейчас → 148 к запуску. Половина может не использоваться.
**Файл:** `services/conductor/safeguards.py` → `LifecycleManager.get_sprawl_report()`
**Решение:**
- Usage analytics: calls/day, last_used, unique_users per agent
- Auto-sunset: 30 дней → SUSPENDED, 90 дней → RETIRED
- `get_sprawl_report()`: total, active, degraded, suspended, retired, never_used, low_usage
- Вызывать ежедневно через APScheduler

### #20: Coordination Tax
**Суть:** 21 агент = 210 потенциальных взаимодействий. Сложность O(n²).
**Файл:** `services/conductor/safeguards.py` → `CoordinationLimiter`
**Решение:**
- MAX_HANDOFFS = 5 per workflow
- MAX_AGENTS_PER_WORKFLOW = 7
- MAX_DEPTH = 3 (уровни вложенности)
- Per-workflow tracking: handoffs count + agents set
- Автоматическая блокировка при превышении лимитов

### #21: Session-Level Observability
**Суть:** Видим отдельные вызовы, но не полную картину от запроса до результата.
**Файл:** `services/conductor/session_trace.py` → `SessionTracer`
**Решение:**
- `correlation_id` генерируется в точке входа, прокидывается через все агенты
- OpenTelemetry-like span model: start_span → end_span с метаданными
- Session replay: `get_replay()` — полная timeline с offset_ms, duration, tokens, cost
- Blame assignment: `get_blame()` — какой агент ошибся, какой самый медленный
- Summary: error_rate, avg_duration, avg_cost, avg_agents_per_session

### #22: UX Trust Gap
**Суть:** Пользователь не видит что происходит. 70% не доверяют AI для сложных задач.
**Файл:** `services/conductor/safeguards.py` → `UXTransparency`
**Решение:**
- Progress streaming: шаг-за-шагом ("Анализирую запрос...", "Проверяю качество...")
- `get_progress()` — текущий шаг, процент, агент, confidence
- `format_explanation()` — "почему этот агент?" для продвинутых пользователей
- 9 предопределённых step messages на русском языке
- Интеграция в pipeline: 5 шагов прогресса per request

### #23: Shadow AI
**Суть:** Незарегистрированные агенты работают без governance.
**Статус:** Заложено архитектурно (Agent Registry = единственный способ деплоя).
**Решение на будущее (ENTERPRISE тир):** inventory scan + alerting.

### #24: Over-Permissioning
**Суть:** Все агенты работают через один API key, одну БД. Нет разделения прав.
**Файл:** `services/conductor/safeguards.py` → `PermissionGuard` + `AGENT_PERMISSIONS`
**Решение:**
- Per-agent tool allowlist: каждый агент знает свои разрешённые инструменты
- Per-agent DB table access: certifier видит regulations, не видит billing
- can_write_db / can_send_external flags per agent
- Default permissions для незарегистрированных агентов (minimal access)
- `check_permission()`, `check_db_access()`, `can_write()`, `can_send_external()`

### #25: Debugging Cost (40% спринта)
**Суть:** Отладка мульти-агентных систем в 3-5x дольше. 40% времени на investigation.
**Файл:** `services/conductor/safeguards.py` → `ErrorTracker` + `ErrorType`
**Решение:**
- 10 типов ошибок: LLM, tool, routing, timeout, permission, validation, deadlock, role_violation, injection, unknown
- Auto-classification: `classify_error()` по типу исключения
- Blame report: `get_blame_report()` — какой агент генерирует больше всего ошибок
- Recent errors: фильтр по агенту, по типу
- Per-agent error counters по типам

---

## Часть 3: Архитектура решения

### Новые файлы
```
services/conductor/safeguards.py    — 550+ строк, 10 классов, решает проблемы 14-20, 22, 24-25
services/conductor/session_trace.py — 300+ строк, 3 класса, решает проблему 21
```

### Обновлённые файлы
```
services/conductor/core.py          — Интеграция safeguards + session_trace в pipeline (12 шагов)
services/conductor/__init__.py      — Экспорты SafeguardsManager, SessionTracer
services/health_monitor.py          — SUSPENDED/RETIRED статусы, suspend()/retire() методы
```

### Pipeline v2 (с safeguards)
```
1.  Session trace: start (correlation_id)
2.  Observability: start trace
3.  Safeguards: latency budget start + UX progress
4.  Metering: check daily limits
5.  Health: check agent availability
6.  Safeguards: pre-route check (lifecycle, coordination, deadlock)
7.  Classify → Route
8.  Execute agent
9.  Safeguards: post-response (role boundary, lifecycle record)
10. Session trace: execute span
11. QA-AGENT: validate (critic pattern)
12. Compliance: AI disclaimer
13. Observability: end trace + cost
14. Session trace: end + blame
15. Metering: record usage
16. DARWIN: background eval
17. UX: complete session
```

### Единая точка входа
```python
from services.conductor.safeguards import get_safeguards
sg = get_safeguards()

# Pre-route
sg.pre_route_check(trace_id, agent_name)

# Inter-agent transfer
sg.inter_agent_transfer(source, target, data, context)

# Post-response
sg.post_response_check(agent_name, response)

# Reports
sg.get_full_report()
```

---

## Часть 4: Приоритеты внедрения

| P | Проблема | Статус | Критичность |
|---|---|---|---|
| P0 | #24 Over-permissioning | Код готов | Безопасность |
| P0 | #15 Latency cascade | Код готов | UX |
| P0 | #22 UX trust gap | Код готов | Adoption |
| P1 | #14 Deadlock detection | Код готов | Reliability |
| P1 | #16 Role confusion | Код готов | Safety |
| P1 | #21 Session observability | Код готов | Debugging |
| P1 | #18 Agent-to-agent attack | Код готов | Security |
| P2 | #17 Agent identity | Код готов | Governance |
| P2 | #19 Agent sprawl | Код готов | Maintenance |
| P2 | #20 Coordination tax | Код готов | Performance |
| P2 | #25 Debugging cost | Код готов | Velocity |
| P3 | #23 Shadow AI | Архитектурно | Enterprise |

---

## Источники (исследования 2025-2026)

- [7 Multi-Agent Failure Modes — TechAhead](https://www.techaheadcorp.com/blog/ways-multi-agent-ai-fails-in-production/)
- [Why AI Agent Pilots Fail — Composio](https://composio.dev/blog/why-ai-agent-pilots-fail-2026-integration-roadmap)
- [AI Agents: Why 95% Fail — Directual](https://www.directual.com/blog/ai-agents-in-2025-why-95-of-corporate-projects-fail)
- [Agentic AI Risks 2026 — Security Boulevard](https://securityboulevard.com/2026/03/a-guide-to-agentic-ai-risks-in-2026/)
- [Agent Observability — Maxim](https://www.getmaxim.ai/articles/5-ai-observability-platforms-for-multi-agent-debugging/)
- [UX and AI in 2026 — CleverIT](https://www.cleveritgroup.com/en/blog/ux-and-ai-in-2026-from-experimentation-to-trust)
- [Agentic AI Governance 2026 — HackerNoon](https://hackernoon.com/agentic-ai-governance-frameworks-2026-risks-oversight-and-emerging-standards)
- [Deloitte AI Agent Orchestration 2026](https://www.deloitte.com/us/en/insights/industry/technology/technology-media-and-telecom-predictions/2026/ai-agent-orchestration.html)
