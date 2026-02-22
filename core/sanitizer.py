"""
core/sanitizer.py — Central artifact detector for TestLab.

Единственный источник истины по артефактам.
Используется text_quality модулем и любым будущим модулем.
Может также использоваться напрямую в agi_daemon.py перед отправкой уведомлений.
"""
import re


# Паттерны артефактов: (regex, название, серьёзность)
# серьёзность: "critical" = точно баг, "warn" = подозрительно
ARTIFACT_PATTERNS = [
    # JSON объекты — критично
    (r'\{["\']?\w+["\']?\s*:', "json_object", "critical"),
    # snake_case переменные — критично
    (r'\b[a-z]{2,}_[a-z]{2,}[a-z_]*\b', "snake_case", "critical"),
    # ISO timestamp — критично
    (r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', "iso_timestamp", "critical"),
    # UUID — критично
    (r'\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b', "uuid", "critical"),
    # Программные литералы — критично
    (r'(?<!\w)(None|null|undefined|NaN|True|False)(?!\w)', "code_literal", "critical"),
    # Markdown заголовки — предупреждение
    (r'^#{1,4} ', "markdown_header", "warn"),
    # Bold markdown — предупреждение
    (r'\*\*[^*]+\*\*', "bold_markdown", "warn"),
    # Блоки кода — критично
    (r'```', "code_block", "critical"),
    # Открытые скобки (JSON/dict признак) — предупреждение
    (r'[{}\[\]]', "brackets", "warn"),
]


def detect_artifacts(text: str) -> list[dict]:
    """
    Возвращает список найденных артефактов.
    Каждый элемент: {"type": str, "severity": str, "match": str}
    """
    if not text or not text.strip():
        return []

    found = []
    seen_types = set()

    for pattern, name, severity in ARTIFACT_PATTERNS:
        flags = re.MULTILINE if name == "markdown_header" else 0
        match = re.search(pattern, text, flags)
        if match and name not in seen_types:
            found.append({
                "type": name,
                "severity": severity,
                "match": match.group(0)[:40],
            })
            seen_types.add(name)

    return found


def has_critical_artifact(text: str) -> tuple[bool, str]:
    """
    Быстрая проверка: есть ли критичные артефакты.
    Возвращает (True, "тип") или (False, "").
    """
    for artifact in detect_artifacts(text):
        if artifact["severity"] == "critical":
            return True, artifact["type"]
    return False, ""


def is_clean(text: str) -> bool:
    """True если нет критичных артефактов."""
    ok, _ = has_critical_artifact(text)
    return not ok


def avg_sentence_length(text: str) -> float:
    """Средняя длина предложения в символах."""
    sentences = re.split(r'[.!?]\s+', text.strip())
    sentences = [s for s in sentences if len(s) > 5]
    if not sentences:
        return 0.0
    return sum(len(s) for s in sentences) / len(sentences)


def sanitize(text: str) -> str:
    """
    Автоматически исправляет артефакты в тексте.
    Используется в agi_daemon.py перед отправкой в Telegram.
    """
    # Убрать JSON объекты
    text = re.sub(r'\{[^}]*\}', '', text)
    # snake_case → слова через пробел
    text = re.sub(r'([a-z]{2,})_([a-z]{2,})', r'\1 \2', text)
    # ISO timestamp → человеческий формат
    text = re.sub(
        r'(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):\d{2}',
        r'\3.\2.\1 в \4:\5',
        text
    )
    # Программные литералы
    text = re.sub(r'\b(None|null|undefined|NaN)\b', '', text)
    # Убрать лишние пробелы
    text = re.sub(r' {2,}', ' ', text).strip()
    return text
