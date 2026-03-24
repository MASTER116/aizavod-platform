"""
База соответствий марок материалов GB → ГОСТ.
Источники: GB/T 700, GB/T 1591, GB/T 699, GB/T 3077, GB/T 20878, GB/T 9439, GB/T 1348
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class MaterialMapping:
    gb_grade: str
    gost_grade: str
    gb_standard: str
    gost_standard: str
    category: str
    description: str
    confidence: float = 1.0  # 1.0 = exact match, 0.8 = approximate


# ─── Конструкционные углеродистые стали (GB/T 700 → ГОСТ 380) ───
STRUCTURAL_CARBON = [
    MaterialMapping("Q195", "Ст1кп", "GB/T 700", "ГОСТ 380-2005", "structural_carbon", "σ_т ~195 МПа"),
    MaterialMapping("Q215A", "Ст2кп", "GB/T 700", "ГОСТ 380-2005", "structural_carbon", "σ_т ~215 МПа, группа А"),
    MaterialMapping("Q215B", "Ст2пс", "GB/T 700", "ГОСТ 380-2005", "structural_carbon", "σ_т ~215 МПа, группа В"),
    MaterialMapping("Q235A", "Ст3кп", "GB/T 700", "ГОСТ 380-2005", "structural_carbon", "σ_т ~235 МПа, группа А"),
    MaterialMapping("Q235B", "Ст3сп", "GB/T 700", "ГОСТ 380-2005", "structural_carbon", "σ_т ~235 МПа, группа В"),
    MaterialMapping("Q235C", "Ст3сп", "GB/T 700", "ГОСТ 380-2005", "structural_carbon", "σ_т ~235 МПа, с ударной вязкостью", 0.9),
    MaterialMapping("Q235D", "Ст3сп", "GB/T 700", "ГОСТ 380-2005", "structural_carbon", "σ_т ~235 МПа, с ударной вязкостью -20°C", 0.85),
    MaterialMapping("Q275", "Ст5сп", "GB/T 700", "ГОСТ 380-2005", "structural_carbon", "σ_т ~275 МПа"),
]

# ─── Низколегированные стали (GB/T 1591 → ГОСТ 19281) ───
LOW_ALLOY = [
    MaterialMapping("Q345A", "09Г2С", "GB/T 1591", "ГОСТ 19281-2014", "low_alloy", "Устаревшее обозначение Q355", 0.9),
    MaterialMapping("Q345B", "09Г2С", "GB/T 1591", "ГОСТ 19281-2014", "low_alloy", "Устаревшее обозначение Q355"),
    MaterialMapping("Q355A", "09Г2С", "GB/T 1591", "ГОСТ 19281-2014", "low_alloy", "σ_т ~355 МПа, группа А"),
    MaterialMapping("Q355B", "09Г2С", "GB/T 1591", "ГОСТ 19281-2014", "low_alloy", "σ_т ~355 МПа, группа В"),
    MaterialMapping("Q355C", "09Г2С", "GB/T 1591", "ГОСТ 19281-2014", "low_alloy", "σ_т ~355 МПа, с ударной вязкостью", 0.95),
    MaterialMapping("Q355D", "09Г2С", "GB/T 1591", "ГОСТ 19281-2014", "low_alloy", "σ_т ~355 МПа, -20°C", 0.9),
    MaterialMapping("Q390B", "14Г2АФ", "GB/T 1591", "ГОСТ 19281-2014", "low_alloy", "σ_т ~390 МПа", 0.85),
    MaterialMapping("Q420B", "15ХСНД", "GB/T 1591", "ГОСТ 19281-2014", "low_alloy", "σ_т ~420 МПа, атмосферостойкая", 0.8),
    MaterialMapping("Q460C", "16Г2АФ", "GB/T 1591", "ГОСТ 19281-2014", "low_alloy", "σ_т ~460 МПа", 0.8),
    MaterialMapping("16Mn", "09Г2С", "GB/T 1591", "ГОСТ 19281-2014", "low_alloy", "Старое обозначение Q345/Q355"),
]

# ─── Качественные углеродистые стали (GB/T 699 → ГОСТ 1050) ───
QUALITY_CARBON = [
    MaterialMapping("08F", "08кп", "GB/T 699", "ГОСТ 1050-2013", "quality_carbon", "Низкоуглеродистая, кипящая"),
    MaterialMapping("08", "08", "GB/T 699", "ГОСТ 1050-2013", "quality_carbon", "C ~0.08%"),
    MaterialMapping("10", "10", "GB/T 699", "ГОСТ 1050-2013", "quality_carbon", "C ~0.10%"),
    MaterialMapping("15", "15", "GB/T 699", "ГОСТ 1050-2013", "quality_carbon", "C ~0.15%"),
    MaterialMapping("20", "20", "GB/T 699", "ГОСТ 1050-2013", "quality_carbon", "C ~0.20%"),
    MaterialMapping("25", "25", "GB/T 699", "ГОСТ 1050-2013", "quality_carbon", "C ~0.25%"),
    MaterialMapping("30", "30", "GB/T 699", "ГОСТ 1050-2013", "quality_carbon", "C ~0.30%"),
    MaterialMapping("35", "35", "GB/T 699", "ГОСТ 1050-2013", "quality_carbon", "C ~0.35%"),
    MaterialMapping("40", "40", "GB/T 699", "ГОСТ 1050-2013", "quality_carbon", "C ~0.40%"),
    MaterialMapping("45", "Сталь 45", "GB/T 699", "ГОСТ 1050-2013", "quality_carbon", "Самая распространённая машиностроительная"),
    MaterialMapping("50", "50", "GB/T 699", "ГОСТ 1050-2013", "quality_carbon", "C ~0.50%"),
    MaterialMapping("55", "55", "GB/T 699", "ГОСТ 1050-2013", "quality_carbon", "C ~0.55%"),
    MaterialMapping("60", "60", "GB/T 699", "ГОСТ 1050-2013", "quality_carbon", "C ~0.60%"),
]

# ─── Легированные конструкционные стали (GB/T 3077 → ГОСТ 4543) ───
ALLOY_STRUCTURAL = [
    MaterialMapping("40Cr", "40Х", "GB/T 3077", "ГОСТ 4543-2016", "alloy_structural", "Хромистая"),
    MaterialMapping("15CrMo", "15ХМ", "GB/T 3077", "ГОСТ 4543-2016", "alloy_structural", "Хромомолибденовая"),
    MaterialMapping("20Cr", "20Х", "GB/T 3077", "ГОСТ 4543-2016", "alloy_structural", "Хромистая цементуемая"),
    MaterialMapping("30CrMo", "30ХМА", "GB/T 3077", "ГОСТ 4543-2016", "alloy_structural", "Хромомолибденовая", 0.9),
    MaterialMapping("35CrMo", "35ХМ", "GB/T 3077", "ГОСТ 4543-2016", "alloy_structural", "Хромомолибденовая"),
    MaterialMapping("42CrMo", "40ХН2МА", "GB/T 3077", "ГОСТ 4543-2016", "alloy_structural", "Хромоникельмолибденовая", 0.85),
    MaterialMapping("20CrMnTi", "18ХГТ", "GB/T 3077", "ГОСТ 4543-2016", "alloy_structural", "Цементуемая"),
    MaterialMapping("30CrMnSi", "30ХГСА", "GB/T 3077", "ГОСТ 4543-2016", "alloy_structural", "Высокопрочная"),
    MaterialMapping("30CrMnSiA", "30ХГСА", "GB/T 3077", "ГОСТ 4543-2016", "alloy_structural", "Высокопрочная"),
    MaterialMapping("40CrNiMoA", "40ХН2МА", "GB/T 3077", "ГОСТ 4543-2016", "alloy_structural", "Хромоникельмолибденовая"),
    MaterialMapping("20CrMnMo", "20ХГМ", "GB/T 3077", "ГОСТ 4543-2016", "alloy_structural", "Цементуемая", 0.85),
]

# ─── Пружинные стали (GB/T 1222 → ГОСТ 14959) ───
SPRING_STEEL = [
    MaterialMapping("65Mn", "65Г", "GB/T 1222", "ГОСТ 14959-2016", "spring", "Марганцовистая пружинная"),
    MaterialMapping("60Si2Mn", "60С2А", "GB/T 1222", "ГОСТ 14959-2016", "spring", "Кремнемарганцовистая", 0.9),
    MaterialMapping("55Si2Mn", "55С2", "GB/T 1222", "ГОСТ 14959-2016", "spring", "Кремнистая пружинная", 0.85),
    MaterialMapping("50CrVA", "50ХФА", "GB/T 1222", "ГОСТ 14959-2016", "spring", "Хромованадиевая"),
]

# ─── Нержавеющие стали (GB/T 20878 → ГОСТ 5632) ───
STAINLESS = [
    MaterialMapping("06Cr19Ni10", "08Х18Н10", "GB/T 20878", "ГОСТ 5632-2014", "stainless", "Аустенитная (AISI 304)"),
    MaterialMapping("0Cr18Ni9", "08Х18Н10", "GB/T 20878", "ГОСТ 5632-2014", "stainless", "Старое обозначение 304"),
    MaterialMapping("022Cr19Ni10", "03Х18Н11", "GB/T 20878", "ГОСТ 5632-2014", "stainless", "Низкоуглеродистая (AISI 304L)"),
    MaterialMapping("06Cr17Ni12Mo2", "08Х17Н13М2Т", "GB/T 20878", "ГОСТ 5632-2014", "stainless", "Молибденовая (AISI 316Ti)", 0.9),
    MaterialMapping("022Cr17Ni12Mo2", "03Х17Н14М3", "GB/T 20878", "ГОСТ 5632-2014", "stainless", "Низкоуглеродистая (AISI 316L)"),
    MaterialMapping("06Cr19Ni10N", "08Х18Н10Т", "GB/T 20878", "ГОСТ 5632-2014", "stainless", "С титаном (AISI 321)", 0.85),
    MaterialMapping("12Cr13", "12Х13", "GB/T 20878", "ГОСТ 5632-2014", "stainless", "Мартенситная (AISI 410)"),
    MaterialMapping("20Cr13", "20Х13", "GB/T 20878", "ГОСТ 5632-2014", "stainless", "Мартенситная (AISI 420)"),
    MaterialMapping("30Cr13", "30Х13", "GB/T 20878", "ГОСТ 5632-2014", "stainless", "Мартенситная"),
    MaterialMapping("12Cr18Ni9", "12Х18Н9", "GB/T 20878", "ГОСТ 5632-2014", "stainless", "Аустенитная"),
    MaterialMapping("12Cr18Ni9Ti", "12Х18Н10Т", "GB/T 20878", "ГОСТ 5632-2014", "stainless", "С титаном"),
]

# ─── Чугуны серые (GB/T 9439 → ГОСТ 1412) ───
GREY_IRON = [
    MaterialMapping("HT100", "СЧ10", "GB/T 9439", "ГОСТ 1412-85", "grey_iron", "σ_в ~100 МПа"),
    MaterialMapping("HT150", "СЧ15", "GB/T 9439", "ГОСТ 1412-85", "grey_iron", "σ_в ~150 МПа"),
    MaterialMapping("HT200", "СЧ20", "GB/T 9439", "ГОСТ 1412-85", "grey_iron", "σ_в ~200 МПа"),
    MaterialMapping("HT250", "СЧ25", "GB/T 9439", "ГОСТ 1412-85", "grey_iron", "σ_в ~250 МПа"),
    MaterialMapping("HT300", "СЧ30", "GB/T 9439", "ГОСТ 1412-85", "grey_iron", "σ_в ~300 МПа"),
    MaterialMapping("HT350", "СЧ35", "GB/T 9439", "ГОСТ 1412-85", "grey_iron", "σ_в ~350 МПа"),
]

# ─── Чугуны высокопрочные (GB/T 1348 → ГОСТ 7293) ───
DUCTILE_IRON = [
    MaterialMapping("QT400-18", "ВЧ40", "GB/T 1348", "ГОСТ 7293-85", "ductile_iron", "σ_в ~400 МПа, δ ~18%"),
    MaterialMapping("QT450-10", "ВЧ45", "GB/T 1348", "ГОСТ 7293-85", "ductile_iron", "σ_в ~450 МПа, δ ~10%"),
    MaterialMapping("QT500-7", "ВЧ50", "GB/T 1348", "ГОСТ 7293-85", "ductile_iron", "σ_в ~500 МПа, δ ~7%"),
    MaterialMapping("QT600-3", "ВЧ60", "GB/T 1348", "ГОСТ 7293-85", "ductile_iron", "σ_в ~600 МПа, δ ~3%"),
    MaterialMapping("QT700-2", "ВЧ70", "GB/T 1348", "ГОСТ 7293-85", "ductile_iron", "σ_в ~700 МПа, δ ~2%"),
    MaterialMapping("QT800-2", "ВЧ80", "GB/T 1348", "ГОСТ 7293-85", "ductile_iron", "σ_в ~800 МПа, δ ~2%"),
]

# ─── Алюминиевые сплавы (GB/T 3190 → ГОСТ 4784) ───
ALUMINUM = [
    MaterialMapping("1060", "АД0", "GB/T 3190", "ГОСТ 4784-2019", "aluminum", "Технический алюминий"),
    MaterialMapping("1100", "АД0", "GB/T 3190", "ГОСТ 4784-2019", "aluminum", "Технический алюминий", 0.9),
    MaterialMapping("2024", "Д16", "GB/T 3190", "ГОСТ 4784-2019", "aluminum", "Дуралюмин"),
    MaterialMapping("5052", "АМг2.5", "GB/T 3190", "ГОСТ 4784-2019", "aluminum", "Магналий", 0.85),
    MaterialMapping("5083", "АМг4.5", "GB/T 3190", "ГОСТ 4784-2019", "aluminum", "Судостроительный", 0.85),
    MaterialMapping("6061", "АД33", "GB/T 3190", "ГОСТ 4784-2019", "aluminum", "Конструкционный"),
    MaterialMapping("6063", "АД31", "GB/T 3190", "ГОСТ 4784-2019", "aluminum", "Профильный"),
    MaterialMapping("7075", "В95", "GB/T 3190", "ГОСТ 4784-2019", "aluminum", "Высокопрочный"),
]

# ─── Медные сплавы ───
COPPER = [
    MaterialMapping("H62", "Л63", "GB/T 5231", "ГОСТ 15527-2004", "copper", "Латунь"),
    MaterialMapping("H68", "Л68", "GB/T 5231", "ГОСТ 15527-2004", "copper", "Латунь"),
    MaterialMapping("QSn6.5-0.1", "БрОФ6.5-0.15", "GB/T 5231", "ГОСТ 5017-2006", "copper", "Бронза оловянная", 0.85),
]


# ─── Объединённая база ───
ALL_MAPPINGS: list[MaterialMapping] = (
    STRUCTURAL_CARBON
    + LOW_ALLOY
    + QUALITY_CARBON
    + ALLOY_STRUCTURAL
    + SPRING_STEEL
    + STAINLESS
    + GREY_IRON
    + DUCTILE_IRON
    + ALUMINUM
    + COPPER
)

# Быстрый поиск по GB-марке (нормализованный ключ)
_GB_INDEX: dict[str, MaterialMapping] = {}
for m in ALL_MAPPINGS:
    key = m.gb_grade.upper().replace(" ", "").replace("-", "")
    _GB_INDEX[key] = m


def lookup_gb(gb_grade: str) -> Optional[MaterialMapping]:
    """Найти ГОСТ-эквивалент по GB-марке."""
    key = gb_grade.upper().replace(" ", "").replace("-", "")
    return _GB_INDEX.get(key)


def search_gb(query: str) -> list[MaterialMapping]:
    """Поиск по подстроке в GB или ГОСТ обозначении."""
    q = query.upper()
    return [m for m in ALL_MAPPINGS if q in m.gb_grade.upper() or q in m.gost_grade.upper()]
