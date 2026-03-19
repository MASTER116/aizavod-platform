"""Generate ZAVOD-II Master Plan v3.0 PDF."""
import os
from fpdf import FPDF


class PDF(FPDF):
    FONT = "DejaVu"  # Will be set dynamically
    def header(self):
        self.set_font(self.FONT, "B", 14)
        self.cell(0, 10, "ZAVOD-II: MASTER PLAN v3.0", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font(self.FONT, "", 9)
        self.cell(0, 6, "2026-03-20 | 21+ agents | 13 military standards | 55-point audit", align="C", new_x="LMARGIN", new_y="NEXT")
        self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.FONT, "I", 8)
        self.cell(0, 10, f"Zavod-ii | {self.page_no()}/{{nb}}", align="C")

    def section(self, title):
        self.set_font(self.FONT, "B", 12)
        self.set_fill_color(30, 30, 60)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(3)

    def subsection(self, title):
        self.set_font(self.FONT, "B", 10)
        self.set_text_color(30, 30, 120)
        self.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)

    def body(self, text):
        self.set_font(self.FONT, "", 9)
        self.multi_cell(0, 5, text)
        self.ln(2)

    def tbl(self, cells, widths, bold=False):
        self.set_font(self.FONT, "B" if bold else "", 8)
        h = 6
        for i, cell in enumerate(cells):
            w = widths[i]
            self.cell(w, h, str(cell)[:int(w / 1.8)], border=1)
        self.ln(h)


def find_font():
    candidates = [
        "C:/Users/khaly/aizavod-platform/static/fonts/DejaVuSans.ttf",
        "C:/Windows/Fonts/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    for root, _, files in os.walk("C:/Users/khaly/aizavod-platform/static"):
        for f in files:
            if "DejaVu" in f and f.endswith(".ttf"):
                return os.path.join(root, f)
    return None


def main():
    font_path = find_font()
    if not font_path:
        print("ERROR: DejaVu font not found")
        return
    if "arial" in font_path.lower():
        bold_path = font_path.replace("arial.ttf", "arialbd.ttf")
        italic_path = font_path.replace("arial.ttf", "ariali.ttf")
        font_family = "Arial"
    else:
        bold_path = font_path.replace("Sans.ttf", "Sans-Bold.ttf")
        italic_path = font_path.replace("Sans.ttf", "Sans-Oblique.ttf")
        font_family = "DejaVu"

    pdf = PDF()
    pdf.add_font(font_family, "", font_path, uni=True)
    pdf.add_font(font_family, "B", bold_path if os.path.exists(bold_path) else font_path, uni=True)
    pdf.add_font(font_family, "I", italic_path if os.path.exists(italic_path) else font_path, uni=True)
    PDF.FONT = font_family
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    # === TITLE ===
    pdf.add_page()
    pdf.ln(30)
    pdf.set_font(font_family, "B", 28)
    pdf.cell(0, 15, "ZAVOD-II", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(font_family, "", 14)
    pdf.cell(0, 10, "Мультиагентная SaaS-платформа", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, "автоматизации бизнеса", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.set_font(font_family, "B", 11)
    pdf.cell(0, 8, "21+ AI-агент | 9 директоров | 291 отрасль | CONDUCTOR v2", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)
    pdf.set_font(font_family, "", 10)
    pdf.cell(0, 7, "13 военных стандартов (8 ГОСТ РВ + 5 MIL-STD)", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, "25 решённых проблем AI-агентных систем", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, "55-point аудит плана разработки", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(20)
    pdf.set_font(font_family, "I", 9)
    pdf.cell(0, 6, "Master Plan v3.0 | 20 марта 2026", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, "zavod-ii.ru | github.com/MASTER116/aizavod-platform", align="C", new_x="LMARGIN", new_y="NEXT")

    # === ARCHITECTURE ===
    pdf.add_page()
    pdf.section("1. АРХИТЕКТУРА")
    pdf.body(
        "Telegram Bot / Web UI / REST API\n"
        "        |\n"
        "FastAPI Gateway + Rate Limiter\n"
        "        |\n"
        "CONDUCTOR v2 (Pipeline 17 шагов с safeguards)\n"
        "    |-- 21+ агентов + QA-AGENT + COMPLIANCE-AGENT\n"
        "    |-- MEMORY (Letta: Core/Recall/Archival)\n"
        "    |-- HEALTH MONITOR + DEADMAN kill-switch\n"
        "    |-- Safeguards: deadlock, latency, role, firewall, permissions\n"
        "        |\n"
        "LLM: Claude (prompt caching) <-> Ollama <-> Cache\n"
        "Circuit Breaker: CLOSED -> OPEN (3 failures) -> HALF_OPEN\n"
        "        |\n"
        "PostgreSQL 16 + Redis 7\n"
        "Observability + Session Trace + Cost Tracking"
    )
    pdf.subsection("Иерархия CONDUCTOR (3 уровня)")
    pdf.body(
        "CEO -> 9 Директоров -> 18 Отделов -> Специалисты\n\n"
        "CTO: Backend, Frontend, DevOps, AI/ML, QA, Security\n"
        "CFO: Бухгалтерия, Аналитика, Фриланс, Гранты\n"
        "CMO: Контент, Outreach, DevRel, SEO\n"
        "COO: Процессы, Партнёры\n"
        "CPO: Сертификация, SaaS\n"
        "CDO: ML/Данные | CHRO: HR | CLO: Юридический"
    )

    # === AGENTS ===
    pdf.add_page()
    pdf.section("2. АГЕНТЫ (21+)")
    agents = [
        ("CEO", "Руководство", "PRO", "Стратегия, декомпозиция"),
        ("Certifier", "Продукт", "ENT", "Сертификация ТС ЕАЭС"),
        ("Opportunity", "Финансы", "PRO", "Гранты, хакатоны"),
        ("Idea Generator", "Финансы", "Free", "Идеи заработка"),
        ("Market Analyzer", "Финансы", "Starter", "Анализ рынка"),
        ("Freelance", "Продажи", "PRO", "Kwork/Upwork"),
        ("Pricing", "Продажи", "Starter", "Оценка, КП"),
        ("Outreach", "Продажи", "Starter", "Холодные продажи"),
        ("Content", "Контент", "Starter", "IG/TikTok/VK"),
        ("Lawyer", "Юрид.", "Free", "Договоры, ИП/ООО"),
        ("Accountant", "Бух.", "Free", "Налоги, отчётность"),
        ("Darwin", "Обучение", "PRO", "Self-learning"),
        ("Guardian", "Безопасн.", "PRO", "Антифрод, injection"),
        ("Guardian IP", "Патенты", "Pro", "Товарные знаки"),
        ("Scholar", "Наука", "Pro", "Гранты, статьи"),
        ("Herald", "PR", "Starter", "Хабр, Product Hunt"),
        ("Namer", "Нейминг", "Free", "Названия, домены"),
        ("Voice", "Голос", "Pro", "Скрипты звонков"),
        ("Treasurer", "Казнач.", "PRO", "Cash flow"),
        ("Oracle", "Аналит.", "Pro", "ML-прогнозы"),
        ("QA-AGENT", "Система", "--", "Critic, PII"),
        ("COMPLIANCE", "Система", "--", "152-ФЗ, PII masking"),
    ]
    w = [35, 28, 18, 109]
    pdf.tbl(["Агент", "Отдел", "Tier", "Описание"], w, bold=True)
    for a in agents:
        pdf.tbl(a, w)

    # === SAFEGUARDS ===
    pdf.add_page()
    pdf.section("3. SAFEGUARDS - 25 РЕШЁННЫХ ПРОБЛЕМ")
    problems = [
        ("#1", "95% проектов умирают", "291 отрасль ОКВЭД, narrow start"),
        ("#2", "Compounding errors", "QA-AGENT (critic pattern)"),
        ("#3", "Dumb RAG", "Letta 3-level memory"),
        ("#4", "Brittle connectors", "CircuitBreaker + Ollama fallback"),
        ("#5", "Polling tax", "Event-driven автономность"),
        ("#6", "Token costs x15", "Prompt caching 90% + routing"),
        ("#7", "Галлюцинации $67B", "QA + DARWIN + ext. thinking"),
        ("#8", "Prompt injection", "FORTRESS + GUARDIAN"),
        ("#9", "Статичные системы", "DARWIN data flywheel"),
        ("#10", "Нет governance", "Audit trail + kill-switch"),
        ("#11", "Build vs Buy", "Мы = vendor, PLG"),
        ("#12", "Легаси не готово", "Telegram-first"),
        ("#13", "152-ФЗ", "COMPLIANCE-AGENT + Selectel"),
        ("#14", "Silent Deadlock", "DeadlockDetector (DFS)"),
        ("#15", "Latency Cascade", "LatencyBudget 10s + parallel"),
        ("#16", "Role Confusion", "RoleBoundaryValidator"),
        ("#17", "Agent Identity", "LifecycleManager (5 states)"),
        ("#18", "Agent-to-Agent Attack", "InterAgentFirewall"),
        ("#19", "Agent Sprawl", "Auto-sunset 30/90 days"),
        ("#20", "Coordination Tax", "Max 5 handoffs"),
        ("#21", "No Session Observability", "SessionTracer"),
        ("#22", "UX Trust Gap", "UXTransparency"),
        ("#24", "Over-Permissioning", "PermissionGuard"),
        ("#25", "Debugging Cost 40%", "ErrorTracker"),
    ]
    w = [10, 45, 135]
    pdf.tbl(["#", "Проблема", "Решение"], w, bold=True)
    for p in problems:
        pdf.tbl(p, w)

    # === MILITARY STANDARDS ===
    pdf.add_page()
    pdf.section("4. ВОЕННЫЕ СТАНДАРТЫ (13)")
    pdf.subsection("Российские (8 ГОСТ)")
    stds = [
        ("ГОСТ РВ 0015-002-2020", "СМК военной продукции", "Конфигурация, аудиты"),
        ("ГОСТ РВ 0015-003-2024", "Проверка СМК", "Trigger-based аудиты"),
        ("ГОСТ Р 51904-2002", "ПО встроенных систем", "5 уровней критичности"),
        ("ГОСТ 27.310-95", "FMEA/FMECA", "S*O*D=RPN per agent"),
        ("ГОСТ Р 56939-2024", "Безопасное ПО", "Secure coding, V&V"),
        ("ГОСТ 19.101-2024", "ЕСПД документы", "6 из 14 типов"),
        ("ГОСТ Р 56920-2024", "Тестирование ПО", "Уровни и методы"),
        ("ГОСТ Р 59194-2020", "Управление требов.", "RTM, baseline"),
    ]
    w = [48, 48, 94]
    pdf.tbl(["Стандарт", "Область", "Что берём"], w, bold=True)
    for s in stds:
        pdf.tbl(s, w)
    pdf.ln(3)
    pdf.subsection("Западные (5 MIL-STD / DO)")
    stds2 = [
        ("MIL-STD-498", "Разработка ПО", "RTM, 6 DID, Review Gates"),
        ("DO-178C", "Safety-critical ПО", "V&V gate, MC/DC"),
        ("MIL-STD-882E", "Сист. безопасность", "Hazard Analysis"),
        ("MIL-STD-1629A", "Анализ отказов", "FMEA/FMECA"),
        ("MIL-HDBK-338B", "Надёжность", "Redundancy"),
    ]
    pdf.tbl(["Стандарт", "Область", "Что берём"], w, bold=True)
    for s in stds2:
        pdf.tbl(s, w)

    pdf.ln(3)
    pdf.subsection("Уровни критичности агентов (ГОСТ Р 51904)")
    crit = [
        ("C (Существенный)", "CERTIFIER, LAWYER, ACCOUNTANT", "QA eval + golden + human"),
        ("D (Незначительный)", "PRICING, OUTREACH, CONTENT..", "QA quick_check"),
        ("E (Без последствий)", "IDEA, SCHOLAR, VOICE", "Базовый QA"),
    ]
    w2 = [40, 70, 80]
    pdf.tbl(["Уровень", "Агенты", "Требования"], w2, bold=True)
    for c in crit:
        pdf.tbl(c, w2)

    # === AUDIT ===
    pdf.add_page()
    pdf.section("5. АУДИТ ПЛАНА (55 пунктов)")
    pdf.body("ЕСТЬ: 20 (36%) | ЧАСТИЧНО: 13 (24%) | НЕТ: 22 (40%)")
    pdf.body("P0 блокеры (7): evaluation, health, canary, logging, backup, secrets, multi-tenancy")
    pdf.body("P1 до клиента (16): тесты, RAG, load, auth, payment, progress, monitoring...")
    pdf.body("P2 масштаб (8): marketplace, SDK, plugin, white-label, SLA, event bus...")

    pdf.ln(2)
    pdf.subsection("P0 Блокеры")
    p0 = [
        ("3.1", "Evaluation Framework", "НЕТ", "Golden set 50+ + RAGAS"),
        ("4.6", "Health Endpoint", "ЧАСТИЧНО", "Добавить dep checks"),
        ("4.7", "Canary / Feature Flags", "НЕТ", "Redis-based flags"),
        ("4.8", "Centralized Logging", "ЧАСТИЧНО", "JSON + ELK/Loki"),
        ("4.9", "Backup / DR", "НЕТ", "pg_dump daily"),
        ("4.10", "Secrets Management", "НЕТ", "Убрать хардкод"),
        ("5.1", "Multi-tenancy", "НЕТ", "tenant_id в models"),
    ]
    w3 = [12, 45, 25, 108]
    pdf.tbl(["#", "Пункт", "Статус", "Решение"], w3, bold=True)
    for p in p0:
        pdf.tbl(p, w3)

    # === ROADMAP ===
    pdf.add_page()
    pdf.section("6. ДОРОЖНАЯ КАРТА")
    pdf.subsection("5 спринтов внедрения военных методов")
    sprints = [
        ("Sprint 1", "P0 блокеры", "Health, secrets, logging, tenant_id, backup"),
        ("Sprint 2", "Военная документация", "RTM, FMEA, Hazard, Architecture"),
        ("Sprint 3", "Тестирование", "Golden 50+, V&V gate, E2E, CI gate"),
        ("Sprint 4", "Продуктовые фичи", "JWT auth, progress, YooKassa, flags"),
        ("Sprint 5", "Config + Operations", "Baseline, runbook, audit, load tests"),
    ]
    w4 = [25, 45, 120]
    pdf.tbl(["Спринт", "Фокус", "Задачи"], w4, bold=True)
    for s in sprints:
        pdf.tbl(s, w4)

    pdf.ln(5)
    pdf.subsection("Общий роадмап проекта")
    pdf.body(
        "Март-Апрель 2026: Фриланс + CERTIFIER MVP + фундамент\n"
        "Апрель-Май: CONDUCTOR + 5 core-агентов + лендинг zavod-ii.ru\n"
        "Май-Июнь: CALL-CENTER MVP + грант РНФ (дедлайн 16.06)\n"
        "Июнь-Июль: Бета 10-20 пользователей\n"
        "Июль-Август: ООО + публичный запуск + ИТ-парк"
    )
    pdf.ln(2)
    pdf.subsection("Финансовая модель")
    pdf.body(
        "Себестоимость: 5700-11500 руб./мес (VPS + Claude API + Pro)\n"
        "Безубыточность: 5 клиентов STARTER = 24950 руб./мес\n"
        "Цель 12 мес: 100 STARTER + 10 PRO = 649000 руб./мес\n\n"
        "Тарифы: FREE (навсегда) / STARTER 4990р / PRO 14990р / ENT 49990р+"
    )
    pdf.ln(2)
    pdf.subsection("Конкуренты")
    pdf.body(
        "Yandex AI Studio: ГЛАВНАЯ УГРОЗА (окно 12-18 мес)\n"
        "Sber GigaChat Enterprise: 15K+ клиентов\n"
        "Наш moat: 291 отрасль + DARWIN + Ollama local + PLG демпинг"
    )

    # Save
    output = "C:/Users/khaly/Desktop/ZAVOD-II_MASTER_PLAN_v3.pdf"
    pdf.output(output)
    print(f"PDF saved: {output}")
    print(f"Pages: {pdf.pages_count}")


if __name__ == "__main__":
    main()
