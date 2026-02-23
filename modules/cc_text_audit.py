"""
CC Text Audit — находит места в cc_template.html / cc_main.py где snake_case
значения из БД отображаются без перевода в human-readable формат.

Cтатический анализ кода — CC не нужен для запуска.
"""
import os
import re

APPS_DIR = "/Users/anvarbakiyev/dronor/apps"

# Сейчас есть в коде (action_type выводится через escapeHtml без маппинга)
# Правильный способ: FORMAT_ACTION_TYPE[t] или t.replace('_', ' ').title()
ACTION_TYPE_LABELS = {
    "telegram_reply":    "Telegram Reply",
    "email_response":    "Email Response",
    "draft_whatsapp":    "WhatsApp Draft",
    "create_task":       "Create Task",
    "document_analysis": "Document Analysis",
    "gui_task":          "GUI Task",
    "review":            "Review",
    "schedule_meeting":  "Schedule Meeting",
    "send_notification": "Send Notification",
    "test":              "Test",
}

AUTO_REPLY_MODE_LABELS = {
    "draft_only":  "Draft Only",
    "semi_auto":   "Semi-Auto",
    "full_auto":   "Full Auto",
}

# Эти все уже есть в коде — проверяем что они действительно используются

# Паттерны которые означают что snake_case отдаётся без перевода:
# - значение поля вставляется напрямую через ${...} / '' +
RAW_RENDER_PATTERNS = [
    # action_type без маппинга
    (r'\$\{escapeHtml\(a\.action_type', 'action_type rendered raw (no label mapping)'),
    (r'\$\{escapeHtml\(t\)', 'type key rendered raw in table (no label)'),
    (r"escapeHtml\(m\)'", 'mode key rendered raw (no label)'),
    (r"escapeHtml\(r\.message_type", 'message_type rendered raw'),
    # Память: ключи отображаются напрямую
    (r"escapeHtml\(k\)", 'memory key rendered raw'),
]

# Паттерны плохого UX текста в UI
BAD_UX_PATTERNS = [
    (r"'\?'", 'fallback "?" shown to user instead of proper empty state'),
    (r'stat-label.*CARS:', 'CARS: prefix in stat label (technical)'),
    (r'font-family:var\(--font-mono\).*action_type', 'action_type in monospace font (looks technical)'),
    (r'Avg Conf\b', 'Abbreviation "Avg Conf" instead of "Avg Confidence"'),
]


def find_js_file():
    """Find the current cc_main_*.js file."""
    import glob
    files = glob.glob(os.path.join(APPS_DIR, "cc_main_*.js"))
    return max(files, key=os.path.getmtime) if files else None


def run(cfg: dict):
    from core.base import TestResult

    js_file = find_js_file()
    template_file = os.path.join(APPS_DIR, "cc_template.html")

    if not js_file:
        return TestResult("fail", "cc_main_*.js not found")

    with open(js_file) as f:
        js = f.read()
    with open(template_file) as f:
        template = f.read()

    issues = []
    warnings = []
    recommendations = []

    # 1. Проверяем есть ли маппинг action_type на labels
    has_action_label_map = 'ACTION_LABELS' in js or 'actionLabels' in js or 'action_labels' in js
    if not has_action_label_map:
        issues.append("No action_type label map found — raw values shown to user")
        recommendations.append(
            "Add to cc_main.js:\n"
            "  const ACTION_LABELS = {\n"
            "    telegram_reply: 'Telegram Reply',\n"
            "    email_response: 'Email Response',\n"
            "    draft_whatsapp: 'WhatsApp Draft',\n"
            "    create_task:    'Create Task',\n"
            "    document_analysis: 'Document Analysis',\n"
            "    gui_task:       'GUI Task',\n"
            "    review:         'Review',\n"
            "    schedule_meeting: 'Schedule Meeting',\n"
            "    send_notification: 'Notification',\n"
            "  };\n"
            "  // Usage: ACTION_LABELS[a.action_type] || a.action_type.replace(/_/g,' ')"
        )

    # 2. Проверяем raw render паттерны
    for pattern, desc in RAW_RENDER_PATTERNS:
        if re.search(pattern, js):
            issues.append(f"{desc}")

    # 3. Плохой UX текст
    for pattern, desc in BAD_UX_PATTERNS:
        if re.search(pattern, js):
            warnings.append(desc)

    # 4. Проверяем auto-reply mode лабелс
    has_ar_labels = 'arL' in js and 'Draft Only' in js
    if has_ar_labels:
        pass  # уже есть
    else:
        issues.append("Auto-reply mode has no human labels")

    # 5. Проверяем memory block ключи
    if 'memory_learning_extractor' in js or 'memory_auto_manager' in js:
        issues.append("Memory block names (expert names) shown as-is — need human labels")
        recommendations.append(
            "Add to cc_main.js:\n"
            "  const MEMORY_BLOCK_LABELS = {\n"
            "    memory_learning_extractor: 'Learning',\n"
            "    memory_auto_manager:       'Auto Manager',\n"
            "    memory_importance_updater: 'Importance',\n"
            "    memory_self_edit:          'Self-Edit',\n"
            "    memory_archival_manager:   'Archival',\n"
            "  };"
        )

    # 6. Проверяем наличие UTM параметров в UI
    if 'utm_source' in js or 'utm_medium' in js:
        warnings.append("UTM parameters visible in UI (utm_source, utm_medium) — should be hidden or labelled")

    # 7. Проверяем отсутствие общей функции formatKey
    has_format_key = 'formatKey' in js or 'humanize' in js
    if not has_format_key:
        recommendations.append(
            "Add universal helper to cc_main.js:\n"
            "  function formatKey(key) {\n"
            "    const MAP = {...ACTION_LABELS, ...MEMORY_BLOCK_LABELS};\n"
            "    return MAP[key] || key.replace(/_/g, ' ').replace(/\\b\\w/g, c => c.toUpperCase());\n"
            "  }\n"
            "  // Replaces all escapeHtml(x.some_snake_field) with formatKey(x.some_snake_field)"
        )

    # Статистика
    total_checks = len(RAW_RENDER_PATTERNS) + len(BAD_UX_PATTERNS) + 4
    detail_lines = []
    if issues:
        detail_lines.append(f"ISSUES ({len(issues)}):")
        detail_lines.extend(f"  \u2717 {i}" for i in issues)
    if warnings:
        detail_lines.append(f"WARNINGS ({len(warnings)}):")
        detail_lines.extend(f"  \u26a0 {w}" for w in warnings)
    if recommendations:
        detail_lines.append(f"RECOMMENDATIONS ({len(recommendations)}):")
        for rec in recommendations:
            detail_lines.append("  ---")
            detail_lines.extend(f"  {line}" for line in rec.split("\n"))
    detail_lines.append(f"\nFile: {os.path.basename(js_file)} ({len(js)//1024}kb)")

    detail = "\n".join(detail_lines)

    if issues:
        return TestResult(
            "warn" if len(issues) <= 3 else "fail",
            f"CC Text Audit: {len(issues)} text issues, {len(warnings)} warnings",
            detail=detail,
            data={"issues": len(issues), "warnings": len(warnings), "recommendations": len(recommendations)}
        )

    return TestResult(
        "pass" if not warnings else "warn",
        f"CC Text Audit: no critical text issues" + (f", {len(warnings)} minor" if warnings else ""),
        detail=detail,
        data={"issues": 0, "warnings": len(warnings)}
    )
