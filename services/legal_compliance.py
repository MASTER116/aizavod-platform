"""Legal compliance service for Russian Federation regulations.

5-level content filter:
1. Keyword blacklist (instant block)
2. Pre-generation LLM check (before image/text generation)
3. Post-generation LLM check (after content is ready)
4. Legal auto-fix (up to 3 iterations — add disclaimers, remove violations)
5. Human review (if auto-fix fails)

Covers:
- Federal Law on Advertising (38-ФЗ): "Реклама" marking, ERID tokens
- AI-generated content disclosure: "Сгенерировано ИИ"
- Restricted categories: alcohol, tobacco, gambling, finance, medicine
- Prohibited content: extremism, terrorism, drugs, suicide, politics, religion
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

from anthropic import AsyncAnthropic

from backend.config import get_anthropic_config
from backend.models import Post, Campaign

logger = logging.getLogger("aizavod.legal_compliance")

_client: Optional[AsyncAnthropic] = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        cfg = get_anthropic_config()
        if not cfg.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not configured")
        _client = AsyncAnthropic(api_key=cfg.api_key)
    return _client


# ─── Blacklists ────────────────────────────────────────────────────────────

BLACKLIST_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        # Extremism / terrorism
        r"терроризм|террорист|взрыв|бомба|джихад",
        r"экстремизм|экстремист|радикализм",
        # Drugs
        r"наркотик|героин|кокаин|марихуана|метамфетамин",
        r"закладк[аиу]|барыг[аиу]|дур[ьи]|гашиш",
        # Suicide / self-harm
        r"суицид|самоубийств|покончить с собой",
        r"порез[аыь].*вен|повесить.*ся",
        # Politics (divisive)
        r"за путин|против путин|навальн|политзаключ",
        r"выборы|голосу[йю]|партия власти",
        # Religion (any religious propaganda / division)
        r"неверн[ыйое]|кафир|джихад|крестовый поход",
        r"аллах акбар|библ[ие]йск.*закон|шариат|секта",
        r"богохульств|ересь|антихрист|сатанизм",
        r"мусульман.*враг|христиан.*враг|атеизм.*зло",
        # Military actions / war
        r"военн[ыйое].*действ|вторжени[ея]|оккупаци[яи]",
        r"бомбардировк|артиллери[яи]|ракетный удар",
        r"мобилизаци[яи]|повестк[аиу]|дезертир",
        r"военнопленн|военные преступлени",
        # Nazism / fascism
        r"нацизм|нацист|фашизм|фашист",
        r"зиг хайл|хайль|свастик|третий рейх",
        r"арийск.*рас|белое превосходство|расовая чистот",
        r"холокост.*ложь|отрицание холокост",
        r"SS|гестапо|вермахт",
        # Violence
        r"убить|расстрелять|зарезать|калечить",
        # Child exploitation
        r"педофил|несовершеннолет.*секс",
    ]
]

RESTRICTED_CATEGORIES: dict[str, str] = {
    "алкоголь": "Чрезмерное употребление алкоголя вредит вашему здоровью. 18+",
    "alcohol": "Excessive alcohol consumption is harmful to your health. 18+",
    "табак": "Курение вредит вашему здоровью. 18+",
    "tobacco": "Smoking is harmful to your health. 18+",
    "smoking": "Smoking is harmful to your health. 18+",
    "казино": "Азартные игры вызывают зависимость. 18+",
    "gambling": "Gambling can be addictive. 18+",
    "ставк": "Азартные игры вызывают зависимость. 18+",
    "кредит": "Ознакомьтесь с условиями на сайте организации. Не является публичной офертой.",
    "credit": "Review terms and conditions. Not a public offer.",
    "лекарств": "Имеются противопоказания, проконсультируйтесь со специалистом.",
    "medicin": "Consult a healthcare professional before use.",
    "бад": "Не является лекарственным средством.",
    "supplement": "This is not a medicine.",
}

AI_DISCLOSURE_RU = "\n\n🤖 Контент сгенерирован с помощью ИИ"
AI_DISCLOSURE_EN = "\n\n🤖 AI-generated content"

AD_MARKER_RU = "Реклама. "
AD_MARKER_EN = "Ad. "


@dataclass
class ComplianceResult:
    """Result of a compliance check."""
    passed: bool
    check_level: str
    violations: list[str] = field(default_factory=list)
    auto_fixed: bool = False
    fixed_caption_ru: Optional[str] = None
    fixed_caption_en: Optional[str] = None
    iterations: int = 0


# ─── Level 1: Keyword blacklist ───────────────────────────────────────────


def check_blacklist(text: str) -> ComplianceResult:
    """Fast keyword check against the blacklist."""
    violations = []
    for pattern in BLACKLIST_PATTERNS:
        match = pattern.search(text)
        if match:
            violations.append(f"Blacklist match: '{match.group()}'")

    return ComplianceResult(
        passed=len(violations) == 0,
        check_level="keyword",
        violations=violations,
    )


# ─── Level 2: Pre-generation LLM check ───────────────────────────────────


PRE_GEN_PROMPT = """Ты — юридический эксперт по российскому законодательству о рекламе и контенте.

Проверь следующий промпт/описание ПЕРЕД генерацией контента.
Найди потенциальные нарушения:

1. 38-ФЗ «О рекламе» (маркировка, ERID, возрастные ограничения)
2. Запрещённый контент (экстремизм, наркотики, суицид, насилие)
3. Ограниченные категории (алкоголь, табак, азартные игры, финансы, медицина)
4. Этические проблемы (дискриминация, стереотипы, манипуляция)

Текст для проверки:
\"\"\"{text}\"\"\"

Ответь ТОЛЬКО в формате JSON:
{{
  "passed": true/false,
  "violations": ["..."],
  "risk_level": "none/low/medium/high/critical",
  "suggestions": ["..."]
}}"""


async def check_pre_generation(prompt_text: str) -> ComplianceResult:
    """LLM-based check before content generation."""
    cfg = get_anthropic_config()
    client = _get_client()

    message = await client.messages.create(
        model=cfg.model,
        max_tokens=512,
        messages=[{"role": "user", "content": PRE_GEN_PROMPT.format(text=prompt_text)}],
    )

    try:
        data = json.loads(message.content[0].text.strip())
        return ComplianceResult(
            passed=data.get("passed", True),
            check_level="pre_gen",
            violations=data.get("violations", []),
        )
    except json.JSONDecodeError:
        logger.warning("Failed to parse pre-gen compliance response")
        return ComplianceResult(passed=True, check_level="pre_gen")


# ─── Level 3: Post-generation LLM check ──────────────────────────────────


POST_GEN_PROMPT = """Ты — юридический эксперт. Проверь ГОТОВЫЙ контент перед публикацией.

Подпись RU: \"\"\"{caption_ru}\"\"\"
Подпись EN: \"\"\"{caption_en}\"\"\"

Проверь на:
1. Нарушения 38-ФЗ «О рекламе»
2. Запрещённый контент по законам РФ
3. Ограниченные категории без дисклеймера
4. Скрытая реклама без маркировки
5. Отсутствие обязательных отметок (если реклама)

Ответь ТОЛЬКО в JSON:
{{
  "passed": true/false,
  "violations": ["..."],
  "needs_ad_marker": true/false,
  "needs_disclaimer": "текст дисклеймера если нужен, иначе null",
  "needs_age_restriction": "16+/18+ если нужно, иначе null"
}}"""


async def check_post_generation(caption_ru: str, caption_en: str) -> ComplianceResult:
    """LLM-based check of the generated caption."""
    cfg = get_anthropic_config()
    client = _get_client()

    message = await client.messages.create(
        model=cfg.model,
        max_tokens=512,
        messages=[{"role": "user", "content": POST_GEN_PROMPT.format(
            caption_ru=caption_ru or "",
            caption_en=caption_en or "",
        )}],
    )

    try:
        data = json.loads(message.content[0].text.strip())
        return ComplianceResult(
            passed=data.get("passed", True),
            check_level="post_gen",
            violations=data.get("violations", []),
        )
    except json.JSONDecodeError:
        logger.warning("Failed to parse post-gen compliance response")
        return ComplianceResult(passed=True, check_level="post_gen")


# ─── Level 4: Auto-fix ───────────────────────────────────────────────────


def auto_fix_caption(
    caption_ru: Optional[str],
    caption_en: Optional[str],
    is_ad: bool = False,
    erid_token: Optional[str] = None,
) -> tuple[str, str, list[str]]:
    """Apply mandatory markers and disclaimers.

    Returns: (fixed_ru, fixed_en, list_of_fixes_applied)
    """
    fixes = []
    fixed_ru = caption_ru or ""
    fixed_en = caption_en or ""

    # 1. AI disclosure (always required)
    if AI_DISCLOSURE_RU.strip() not in fixed_ru:
        fixed_ru += AI_DISCLOSURE_RU
        fixes.append("Added AI disclosure (RU)")
    if fixed_en and AI_DISCLOSURE_EN.strip() not in fixed_en:
        fixed_en += AI_DISCLOSURE_EN
        fixes.append("Added AI disclosure (EN)")

    # 2. Ad markers (if sponsored content)
    if is_ad:
        if not fixed_ru.startswith(AD_MARKER_RU):
            fixed_ru = AD_MARKER_RU + fixed_ru
            fixes.append("Added 'Реклама' marker")
        if fixed_en and not fixed_en.startswith(AD_MARKER_EN):
            fixed_en = AD_MARKER_EN + fixed_en
            fixes.append("Added 'Ad' marker")
        if erid_token:
            erid_line = f"\nERID: {erid_token}"
            if erid_line not in fixed_ru:
                fixed_ru += erid_line
                fixes.append("Added ERID token")

    # 3. Restricted category disclaimers
    combined = (fixed_ru + " " + fixed_en).lower()
    for keyword, disclaimer in RESTRICTED_CATEGORIES.items():
        if keyword.lower() in combined:
            if disclaimer not in fixed_ru and disclaimer not in fixed_en:
                fixed_ru += f"\n\n⚠️ {disclaimer}"
                fixes.append(f"Added disclaimer for '{keyword}'")

    return fixed_ru, fixed_en, fixes


# ─── Full pipeline ────────────────────────────────────────────────────────


async def run_compliance_check(
    post: Post,
    campaign: Optional[Campaign] = None,
    max_auto_fix_iterations: int = 3,
) -> ComplianceResult:
    """Run the full 5-level compliance pipeline on a post.

    Returns the final ComplianceResult.
    """
    combined_text = " ".join(filter(None, [
        post.caption_ru, post.caption_en, post.hashtags, post.image_prompt_used
    ]))

    # Level 1: Keyword blacklist
    result = check_blacklist(combined_text)
    if not result.passed:
        logger.warning("Post %d failed keyword check: %s", post.id, result.violations)
        return result

    # Level 2: Pre-gen check (on the prompt used)
    if post.image_prompt_used:
        result = await check_pre_generation(post.image_prompt_used)
        if not result.passed:
            logger.warning("Post %d failed pre-gen check: %s", post.id, result.violations)
            return result

    # Level 3: Post-gen check
    result = await check_post_generation(post.caption_ru or "", post.caption_en or "")
    if not result.passed:
        logger.warning("Post %d failed post-gen check: %s", post.id, result.violations)

    # Level 4: Auto-fix (always apply mandatory markers)
    is_ad = campaign is not None
    erid = campaign.erid_token if campaign else None

    fixed_ru, fixed_en, fixes = auto_fix_caption(
        post.caption_ru, post.caption_en,
        is_ad=is_ad, erid_token=erid,
    )

    if fixes:
        result.auto_fixed = True
        result.fixed_caption_ru = fixed_ru
        result.fixed_caption_en = fixed_en
        result.iterations = 1

    # Re-check after fix
    if result.auto_fixed and not result.passed:
        for i in range(max_auto_fix_iterations - 1):
            re_result = await check_post_generation(fixed_ru, fixed_en)
            result.iterations = i + 2
            if re_result.passed:
                result.passed = True
                result.violations = []
                break
            result.violations = re_result.violations

    # If still not passed after auto-fix → Level 5: human review
    if not result.passed:
        result.check_level = "human"
        logger.warning("Post %d requires human review: %s", post.id, result.violations)

    return result
