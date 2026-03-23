"""Route handlers — маршрутизация к конкретным агентам."""

from __future__ import annotations


async def _route_ceo(query: str) -> str:
    from services.ceo_agent import get_ceo_agent
    ceo = get_ceo_agent()
    return await ceo.process_question(query)


async def _route_certifier(query: str) -> str:
    from services.certifier_service import get_certifier
    certifier = get_certifier()
    result = await certifier.ask(query)
    return result.get("answer", str(result))


async def _route_opportunities(query: str) -> str:
    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()
    if any(kw in query.lower() for kw in ["найди", "поиск", "сканир", "покажи"]):
        results = await scanner.scan_web()
        if not results:
            return "Ничего не найдено по текущим запросам."
        lines = [f"Найдено: {len(results)} возможностей\n"]
        for i, r in enumerate(results[:10], 1):
            lines.append(f"{i}. {r.title}")
            if r.description:
                lines.append(f"   {r.description[:120]}")
            lines.append(f"   {r.url} | {r.type}\n")
        return "\n".join(lines)
    return await scanner.generate_ideas()


async def _route_ideas(query: str) -> str:
    from services.opportunity_scanner import get_scanner
    scanner = get_scanner()
    return await scanner.generate_ideas()


async def _route_market(query: str) -> str:
    from services.market_analyzer import get_analyzer
    analyzer = get_analyzer()
    if any(kw in query.lower() for kw in ["конкурент", "competitor"]):
        return await analyzer.analyze_competitors(query)
    elif any(kw in query.lower() for kw in ["заявк", "предложен", "proposal"]):
        return await analyzer.generate_proposal(query, "")
    else:
        return await analyzer.quick_market_scan(query)


async def _route_freelance(query: str) -> str:
    from services.freelance_agent import get_freelance_agent
    agent = get_freelance_agent()
    if any(kw in query.lower() for kw in ["найди", "поиск", "заказ"]):
        orders = await agent.search_orders()
        if not orders:
            return "Заказы не найдены."
        lines = [f"Найдено: {len(orders)} заказов\n"]
        for i, o in enumerate(orders[:10], 1):
            lines.append(f"{i}. {o.title[:80]}")
            if o.budget:
                lines.append(f"   Бюджет: {o.budget}")
            lines.append(f"   {o.url} | {o.platform}\n")
        return "\n".join(lines)
    if any(kw in query.lower() for kw in ["kwork", "услуг"]):
        return await agent.create_kwork_services()
    return await agent.list_services()


async def _route_pricing(query: str) -> str:
    from services.pricing_agent import get_pricing_agent
    agent = get_pricing_agent()
    return await agent.estimate_project(query)


async def _route_outreach(query: str) -> str:
    from services.outreach_agent import get_outreach_agent
    agent = get_outreach_agent()
    if any(kw in query.lower() for kw in ["лид", "канал", "где найти"]):
        return await agent.find_leads(query)
    elif any(kw in query.lower() for kw in ["письм", "сообщен", "email", "холодн"]):
        return await agent.generate_cold_message(query, "email")
    else:
        return await agent.list_segments()


async def _route_content(query: str) -> str:
    return (
        "Фабрика контента (Instagram Factory):\n\n"
        "Доступные действия:\n"
        "- Генерация изображений (fal.ai Flux Pro)\n"
        "- Генерация подписей (Claude API)\n"
        "- Публикация в Instagram/TikTok\n"
        "- Расписание постов\n\n"
        "Статус: Instagram логин заблокирован (ChallengeRequired).\n"
        "Генерация контента работает, публикация приостановлена."
    )


async def _route_lawyer(query: str) -> str:
    from services.lawyer_agent import get_lawyer_agent
    agent = get_lawyer_agent()
    q = query.lower()
    if any(kw in q for kw in ["договор", "контракт"]):
        return await agent.check_contract(query)
    elif any(kw in q for kw in ["регистрац", "открыть ип", "зарегистр"]):
        return await agent.ip_registration(query)
    elif any(kw in q for kw in ["трудов", "увольнен", "сотрудник", "работник"]):
        return await agent.labor_law(query)
    return await agent.consult(query)


async def _route_accountant(query: str) -> str:
    from services.accountant_agent import get_accountant_agent
    agent = get_accountant_agent()
    q = query.lower()
    if any(kw in q for kw in ["усн", "осн", "патент", "систем налог", "какой налог"]):
        return await agent.compare_tax_systems(query, "", "")
    elif any(kw in q for kw in ["календар", "отчетност", "когда сдавать", "срок"]):
        return await agent.reporting_calendar()
    elif any(kw in q for kw in ["зарплат", "ндфл", "оклад", "выплат"]):
        return await agent.payroll_calc(query)
    return await agent.consult(query)


async def _route_darwin(query: str) -> str:
    from services.darwin_agent import get_darwin_agent
    agent = get_darwin_agent()
    q = query.lower()
    if any(kw in q for kw in ["оптимиз", "промпт", "улучш"]):
        return await agent.optimize_prompt("unknown", query, "")
    elif any(kw in q for kw in ["отчёт", "отчет", "неделя", "итог"]):
        return await agent.weekly_report(query)
    elif any(kw in q for kw in ["паттерн", "лог", "маршрут"]):
        return await agent.detect_patterns(query)
    return await agent.analyze_response("unknown", query, "")


async def _route_guardian(query: str) -> str:
    from services.guardian_agent import get_guardian_agent
    agent = get_guardian_agent()
    q = query.lower()
    if any(kw in q for kw in ["проверь ввод", "input", "injection"]):
        return await agent.check_input(query)
    elif any(kw in q for kw in ["поведен", "активност", "мультиаккаунт"]):
        return await agent.analyze_user_behavior(query)
    elif any(kw in q for kw in ["отчёт", "отчет", "угроз"]):
        return await agent.threat_report()
    return await agent.check_input(query)


async def _route_scholar(query: str) -> str:
    from services.scholar_agent import get_scholar_agent
    agent = get_scholar_agent()
    q = query.lower()
    if any(kw in q for kw in ["грант", "заявк", "рнф", "фси"]):
        fund = "РНФ" if "рнф" in q else "ФСИ" if "фси" in q else ""
        return await agent.write_grant(query, fund)
    elif any(kw in q for kw in ["литобзор", "обзор литератур", "что написано"]):
        return await agent.literature_review(query)
    elif any(kw in q for kw in ["оформ", "гост", "вак", "стать"]):
        return await agent.format_article(query)
    return await agent.research_question(query)


async def _route_herald(query: str) -> str:
    from services.herald_agent import get_herald_agent
    agent = get_herald_agent()
    q = query.lower()
    if any(kw in q for kw in ["readme"]):
        return await agent.write_readme(query, "")
    elif any(kw in q for kw in ["habr", "хабр", "стать"]):
        return await agent.write_habr_article(query)
    elif any(kw in q for kw in ["телеграм", "telegram", "пост"]):
        return await agent.telegram_post(query)
    elif any(kw in q for kw in ["product hunt", "запуск"]):
        return await agent.product_hunt_launch(query, "")
    return await agent.oss_strategy(query)


async def _route_namer(query: str) -> str:
    from services.namer_agent import get_namer_agent
    agent = get_namer_agent()
    q = query.lower()
    if any(kw in q for kw in ["проверь", "доступн", "занят"]):
        return await agent.check_availability(query)
    elif any(kw in q for kw in ["полн", "цикл", "от и до"]):
        return await agent.full_naming(query)
    return await agent.generate_names(query)


async def _route_guardian_ip(query: str) -> str:
    from services.guardian_ip_agent import get_guardian_ip_agent
    agent = get_guardian_ip_agent()
    q = query.lower()
    if any(kw in q for kw in ["товарн знак", "фипс", "мкту"]):
        return await agent.check_trademark(query)
    elif any(kw in q for kw in ["патент", "изобретен"]):
        return await agent.check_patent(query)
    elif any(kw in q for kw in ["домен", "whois"]):
        return await agent.domain_analysis(query)
    return await agent.ip_audit(query)


async def _route_voice(query: str) -> str:
    from services.voice_agent import get_voice_agent
    agent = get_voice_agent()
    q = query.lower()
    if any(kw in q for kw in ["делов", "переговор", "партнёр"]):
        return await agent.business_call_script(query, "")
    elif any(kw in q for kw in ["продаж", "продающ", "холодн"]):
        return await agent.sales_script(query, "")
    elif any(kw in q for kw in ["tts", "озвуч", "оптимиз"]):
        return await agent.tts_optimize(query)
    return await agent.routine_call_script(query)


async def _route_treasurer(query: str) -> str:
    from services.treasurer_agent import get_treasurer_agent
    agent = get_treasurer_agent()
    q = query.lower()
    if any(kw in q for kw in ["расход", "затрат", "оптимиз"]):
        return await agent.analyze_expenses(query)
    elif any(kw in q for kw in ["доход", "заработ", "источник"]):
        return await agent.find_income_sources(query, "")
    elif any(kw in q for kw in ["cash flow", "денежн", "поток", "прогноз"]):
        return await agent.cash_flow_plan(query, "")
    elif any(kw in q for kw in ["цен", "тариф", "ценообразован"]):
        return await agent.pricing_strategy(query)
    return await agent.find_income_sources(query, "")


async def _route_review_manager(query: str) -> str:
    from services.review_manager_agent import get_review_manager_agent
    agent = get_review_manager_agent()
    return await agent.process_query(query)


async def _route_oracle(query: str) -> str:
    from services.oracle_agent import get_oracle_agent
    agent = get_oracle_agent()
    return await agent.process(query)


# Маппинг имя handler → функция
ROUTE_HANDLERS = {
    "_route_ceo": _route_ceo,
    "_route_certifier": _route_certifier,
    "_route_opportunities": _route_opportunities,
    "_route_ideas": _route_ideas,
    "_route_market": _route_market,
    "_route_freelance": _route_freelance,
    "_route_pricing": _route_pricing,
    "_route_outreach": _route_outreach,
    "_route_content": _route_content,
    "_route_lawyer": _route_lawyer,
    "_route_accountant": _route_accountant,
    "_route_darwin": _route_darwin,
    "_route_guardian": _route_guardian,
    "_route_scholar": _route_scholar,
    "_route_herald": _route_herald,
    "_route_namer": _route_namer,
    "_route_guardian_ip": _route_guardian_ip,
    "_route_voice": _route_voice,
    "_route_treasurer": _route_treasurer,
    "_route_review_manager": _route_review_manager,
    "_route_oracle": _route_oracle,
}
