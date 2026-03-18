"""Иерархия CONDUCTOR: директора, отделы, специалисты."""

DIRECTORS = {
    "cto": {
        "title": "Технический директор (CTO)",
        "departments": ["backend", "frontend", "devops", "ai_ml", "security", "qa"],
        "scope": "Архитектура, код, инфраструктура, DevOps, AI/ML, безопасность, тестирование",
    },
    "cfo": {
        "title": "Финансовый директор (CFO)",
        "departments": ["accounting", "grants", "freelance", "analytics"],
        "scope": "Финансы, бюджет, гранты, фриланс, unit-экономика, налоги",
    },
    "cmo": {
        "title": "Маркетинговый директор (CMO)",
        "departments": ["content", "seo", "devrel", "outreach"],
        "scope": "Маркетинг, контент, соцсети, PR, DevRel, продвижение",
    },
    "coo": {
        "title": "Операционный директор (COO)",
        "departments": ["processes", "partners", "support"],
        "scope": "Операции, процессы, автоматизация, партнёры, поддержка",
    },
    "cpo": {
        "title": "Продуктовый директор (CPO)",
        "departments": ["certifier", "saas", "research"],
        "scope": "Продукт, roadmap, фичи, UX, приоритизация бэклога",
    },
    "cdo": {
        "title": "Дизайн-директор (CDO)",
        "departments": ["uiux", "brand", "motion"],
        "scope": "Дизайн, UI/UX, брендинг, промдизайн, анимации",
    },
    "chro": {
        "title": "HR-директор (CHRO)",
        "departments": ["hiring", "culture"],
        "scope": "Кадры, найм, обучение, культура, аутсорс",
    },
    "clo": {
        "title": "Юридический директор (CLO)",
        "departments": ["ip", "contracts", "registration"],
        "scope": "Юридическое, договоры, IP, патенты, регистрация, compliance",
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
