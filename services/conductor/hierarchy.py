"""Иерархия CONDUCTOR: директора, отделы, специалисты."""

DIRECTORS = {
    "cto": {
        "title": "Технический директор (CTO)",
        "departments": ["backend", "frontend", "devops", "ai_ml", "security", "qa"],
        "scope": "Архитектура, код, инфраструктура, DevOps, AI/ML, безопасность, тестирование",
        "capabilities": [
            "FastAPI backend (REST API, SQLAlchemy, Pydantic v2)",
            "Telegram-боты (aiogram 3, FSM, handlers, keyboards)",
            "RAG-системы (ChromaDB, Claude API, embeddings)",
            "Docker Compose (сборка, деплой, мониторинг)",
            "CI/CD (GitHub Actions, SSH deploy)",
            "LLM-интеграции (Claude API, Ollama, prompt engineering)",
            "PostgreSQL (миграции Alembic, модели SQLAlchemy)",
            "Redis (кэш, очереди Celery, rate limiting)",
            "Тестирование (pytest, unit/integration/adversarial/golden)",
        ],
        "existing_tools": [
            "CertifierService — RAG по сертификации ТС ЕАЭС",
            "LLMClient — Claude API с circuit breaker + Ollama fallback",
            "Docker Compose — 9 контейнеров уже настроено и работают",
            "CONDUCTOR — оркестратор с safeguards и scope classifier",
            "Health Monitor, Session Trace, Observability",
        ],
    },
    "cfo": {
        "title": "Финансовый директор (CFO)",
        "departments": ["accounting", "grants", "freelance", "analytics"],
        "scope": "Финансы, бюджет, гранты, фриланс, unit-экономика, налоги",
        "capabilities": [
            "Финансовое моделирование (unit-экономика, LTV/CAC)",
            "Поиск грантов и конкурсов (РНФ, ФАСИ, Сколково)",
            "Фриланс-заказы (Kwork, оценка ТЗ, отклики)",
            "Бухгалтерия (УСН/ОСН, налоги, отчётность)",
        ],
        "existing_tools": [
            "opportunity_scanner — поиск грантов/хакатонов",
            "freelance_agent — заказы Kwork",
            "accountant_agent — налоги, отчётность",
            "treasurer_agent — cash flow, монетизация",
            "Billing/Metering — кредитная система тарифов",
        ],
    },
    "cmo": {
        "title": "Маркетинговый директор (CMO)",
        "departments": ["content", "seo", "devrel", "outreach"],
        "scope": "Маркетинг, контент, соцсети, PR, DevRel, продвижение",
        "capabilities": [
            "Контент для соцсетей (Instagram, TikTok, VK)",
            "SEO/ASO оптимизация",
            "DevRel (Хабр, Product Hunt, GitHub)",
            "Email-маркетинг, холодные продажи",
        ],
        "existing_tools": [
            "content_factory — генерация контента",
            "outreach_agent — холодные продажи, письма",
            "herald_agent — Хабр, Product Hunt",
        ],
    },
    "coo": {
        "title": "Операционный директор (COO)",
        "departments": ["processes", "partners", "support"],
        "scope": "Операции, процессы, автоматизация, партнёры, поддержка",
        "capabilities": [
            "Автоматизация процессов (n8n, Celery, APScheduler)",
            "Партнёрские интеграции",
            "Поддержка клиентов",
        ],
        "existing_tools": [
            "n8n — визуальная автоматизация (контейнер работает)",
            "Celery + APScheduler — фоновые задачи",
        ],
    },
    "cpo": {
        "title": "Продуктовый директор (CPO)",
        "departments": ["certifier", "saas", "research"],
        "scope": "Продукт, roadmap, фичи, UX, приоритизация бэклога",
        "capabilities": [
            "Продуктовая стратегия и roadmap",
            "Приоритизация фич (ICE, RICE)",
            "UX-исследования, CustDev",
            "Спецификации и PRD",
        ],
        "existing_tools": [
            "certifier — ядро продукта (сертификация ТС ЕАЭС)",
            "291 ОКВЭД уже проклассифицировано",
        ],
    },
    "cdo": {
        "title": "Дизайн-директор (CDO)",
        "departments": ["uiux", "brand", "motion"],
        "scope": "Дизайн, UI/UX, брендинг, промдизайн, анимации",
        "capabilities": [
            "UI/UX дизайн (веб, мобайл, дашборды)",
            "Брендинг и айдентика",
            "Анимации и видео",
        ],
        "existing_tools": [
            "Лендинг zavod-ii уже создан (HTML/CSS)",
            "Frontend — web-ui/dist + frontend/core.html",
        ],
    },
    "chro": {
        "title": "HR-директор (CHRO)",
        "departments": ["hiring", "culture"],
        "scope": "Кадры, найм, обучение, культура, аутсорс",
        "capabilities": [
            "Рекрутинг и найм",
            "Обучение и онбординг",
        ],
        "existing_tools": [],
    },
    "clo": {
        "title": "Юридический директор (CLO)",
        "departments": ["ip", "contracts", "registration"],
        "scope": "Юридическое, договоры, IP, патенты, регистрация, compliance",
        "capabilities": [
            "Договоры (оферта, NDA, ГПХ)",
            "Регистрация ИП/ООО",
            "Товарные знаки и патенты",
            "152-ФЗ compliance",
        ],
        "existing_tools": [
            "lawyer_agent — договоры, регистрация",
            "guardian_ip_agent — товарные знаки, патенты",
            "COMPLIANCE-AGENT — 152-ФЗ, PII masking",
            "aizavod-legal — юридические страницы (terms, privacy)",
        ],
    },
}

DEPARTMENT_SPECIALISTS = {
    "cto.backend": [
        {"code": "fastapi_dev", "title": "FastAPI разработчик"},
        {"code": "db_admin", "title": "Администратор БД"},
        {"code": "api_designer", "title": "Архитектор API"},
    ],
    "cto.frontend": [
        {"code": "react_developer", "title": "React разработчик"},
        {"code": "web_designer", "title": "Веб-разработчик"},
        {"code": "ui_developer", "title": "UI-компонентщик"},
    ],
    "cto.devops": [
        {"code": "docker_engineer", "title": "Docker-инженер"},
        {"code": "ci_cd_specialist", "title": "CI/CD специалист"},
        {"code": "monitoring_engineer", "title": "Инженер мониторинга"},
    ],
    "cto.ai": [
        {"code": "prompt_engineer", "title": "Промпт-инженер"},
        {"code": "rag_specialist", "title": "RAG специалист"},
        {"code": "ml_engineer", "title": "ML-инженер"},
    ],
    "cto.security": [
        {"code": "security_analyst", "title": "Аналитик безопасности"},
        {"code": "penetration_tester", "title": "Пентестер"},
    ],
    "cto.qa": [
        {"code": "qa_engineer", "title": "QA-инженер"},
        {"code": "automation_tester", "title": "Автотестер"},
    ],
    "cfo.accounting": [
        {"code": "accountant", "title": "Бухгалтер"},
        {"code": "tax_advisor", "title": "Налоговый консультант"},
    ],
    "cfo.grants": [
        {"code": "grant_writer", "title": "Составитель заявок"},
        {"code": "rnf_specialist", "title": "Специалист РНФ"},
    ],
    "cfo.freelance": [
        {"code": "order_finder", "title": "Поисковик заказов"},
        {"code": "proposal_writer", "title": "Составитель откликов"},
    ],
    "cfo.analytics": [
        {"code": "financial_analyst", "title": "Финансовый аналитик"},
        {"code": "unit_economist", "title": "Юнит-экономист"},
    ],
    "cmo.content": [
        {"code": "copywriter", "title": "Копирайтер"},
        {"code": "instagram_creator", "title": "Instagram контент-мейкер"},
        {"code": "video_maker", "title": "Видеомейкер"},
    ],
    "cmo.seo": [
        {"code": "seo_specialist", "title": "SEO специалист"},
        {"code": "aso_specialist", "title": "ASO специалист"},
    ],
    "cmo.devrel": [
        {"code": "habr_writer", "title": "Автор Хабр"},
        {"code": "github_maintainer", "title": "GitHub мейнтейнер"},
        {"code": "community_manager", "title": "Комьюнити менеджер"},
    ],
    "cmo.outreach": [
        {"code": "lead_generator", "title": "Лидогенератор"},
        {"code": "email_marketer", "title": "Email маркетолог"},
        {"code": "cold_caller", "title": "Холодные звонки"},
    ],
    "coo.processes": [
        {"code": "process_engineer", "title": "Инженер процессов"},
        {"code": "n8n_developer", "title": "n8n разработчик"},
    ],
    "coo.partners": [
        {"code": "partner_manager", "title": "Менеджер партнёрств"},
        {"code": "integration_specialist", "title": "Специалист по интеграциям"},
    ],
    "coo.support": [
        {"code": "support_agent", "title": "Агент поддержки"},
        {"code": "onboarding_specialist", "title": "Специалист онбординга"},
    ],
    "cpo.certifier": [
        {"code": "certification_expert", "title": "Эксперт по сертификации"},
        {"code": "regulation_analyst", "title": "Аналитик регламентов"},
    ],
    "cpo.saas": [
        {"code": "product_manager", "title": "Продакт-менеджер"},
        {"code": "feature_designer", "title": "Дизайнер фич"},
    ],
    "cpo.research": [
        {"code": "ux_researcher", "title": "UX-исследователь"},
        {"code": "custdev_interviewer", "title": "CustDev интервьюер"},
    ],
    "cdo.uiux": [
        {"code": "web_designer", "title": "Веб-дизайнер"},
        {"code": "mobile_designer", "title": "Мобильный дизайнер"},
        {"code": "dashboard_designer", "title": "Дизайнер дашбордов"},
    ],
    "cdo.brand": [
        {"code": "brand_designer", "title": "Бренд-дизайнер"},
        {"code": "identity_creator", "title": "Создатель айдентики"},
    ],
    "cdo.motion": [
        {"code": "animator", "title": "Аниматор"},
        {"code": "video_editor", "title": "Видеомонтажёр"},
        {"code": "intro_creator", "title": "Создатель интро"},
    ],
    "clo.ip": [
        {"code": "trademark_analyst", "title": "Аналитик товарных знаков"},
        {"code": "patent_specialist", "title": "Патентный специалист"},
    ],
    "clo.contracts": [
        {"code": "contract_lawyer", "title": "Юрист по договорам"},
        {"code": "nda_specialist", "title": "Специалист NDA"},
    ],
    "clo.registration": [
        {"code": "registration_specialist", "title": "Специалист по регистрации"},
        {"code": "license_manager", "title": "Менеджер лицензий"},
    ],
    "chro.hiring": [
        {"code": "recruiter", "title": "Рекрутер"},
        {"code": "technical_interviewer", "title": "Технический интервьюер"},
    ],
    "chro.culture": [
        {"code": "training_manager", "title": "Менеджер обучения"},
        {"code": "culture_specialist", "title": "Специалист по культуре"},
    ],
}
