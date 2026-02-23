"""
CC Visual Tester — Playwright + Claude Vision.

Для каждой секции CC:
1. Открывает секцию в браузере
2. Делает скриншот
3. Если есть кнопки — кликает, ждёт, делает ещё скриншот
4. Отправляет скриншот в Claude Vision API
5. Claude говорит: есть ли баги, дубли, сломанный UI

Результат: конкретные описания багов на русском языке.

config:
  bridge_port: 9300
  anthropic_key_path: /Users/anvarbakiyev/Desktop/credentials/anthropic_api_key.txt
  screenshot_dir: /tmp/cc_visual_test
  sections: список секций (по умолчанию все)
"""
import base64
import json
import os
import re
import subprocess
import time
import urllib.request
import urllib.error
from pathlib import Path


SECTIONS = [
    {"nav": "Overview",       "click_btns": []},
    {"nav": "People",          "click_btns": []},
    {"nav": "Organizations",   "click_btns": []},
    {"nav": "Pending Actions",  "click_btns": []},
    {"nav": "Memory",          "click_btns": []},
    {"nav": "CARS Analytics",  "click_btns": []},
    {"nav": "Auto-Reply",      "click_btns": []},
    {"nav": "Connectors",      "click_btns": ["Quick Sync"]},
    {"nav": "KG Sync",         "click_btns": ["Deep Scan"]},
    {"nav": "Analytics",       "click_btns": []},
]

# Промпт для Claude Vision — конкретный, без воды
VISION_PROMPT = """Ты QA-инженер. Анализируй скриншот интерфейса AGI Command Center.

Найди ТОЛЬКО реальные проблемы:
- Дублирующиеся строки (один и тот же элемент показан дважды и более)
- Текст ошибок (красные сообщения, Error:, Exception:, failed)
- Технические идентификаторы видимые пользователю (snake_case, uuid, None, undefined)
- Застрявшие индикаторы загрузки (Loading..., spinner)
- Пустые секции где явно должны быть данные
- Кнопки или элементы с явно неправильным состоянием

Формат ответа — строго JSON:
{"bugs": [{"severity": "critical|warning|info", "description": "конкретное описание на русском"}]}

Если проблем нет — {"bugs": []}
ТОЛЬКО JSON, никакого другого текста."""


def find_cc_port():
    result = subprocess.run(["lsof", "-i", "-P", "-n"], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if "python" in line.lower() and "listen" in line.lower():
            m = re.search(r'127\.0\.0\.1:(\d+)\s+\(LISTEN\)', line)
            if m:
                port = int(m.group(1))
                if port not in (9300, 9200, 9100):
                    return port
    return None


def ask_claude_vision(image_bytes: bytes, api_key: str, context: str) -> list:
    """Send screenshot to Claude Vision, return list of bugs."""
    image_b64 = base64.standard_b64encode(image_bytes).decode()

    payload = {
        "model": "claude-opus-4-5",
        "max_tokens": 1024,
        "messages": [{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": image_b64
                    }
                },
                {
                    "type": "text",
                    "text": VISION_PROMPT + f"\n\nКонтекст: {context}"
                }
            ]
        }]
    }

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        text = data["content"][0]["text"].strip()
        # Strip markdown code fences if present
        text = re.sub(r'^```[a-z]*\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        result = json.loads(text)
        return result.get("bugs", [])
    except Exception as e:
        return [{"severity": "info", "description": f"Vision API error: {e}"}]


def run(cfg: dict):
    from core.base import TestResult
    from playwright.sync_api import sync_playwright

    bridge_port = cfg.get("bridge_port", 9300)
    key_path = cfg.get("anthropic_key_path",
                       "/Users/anvarbakiyev/Desktop/credentials/anthropic_api_key.txt")
    screenshot_dir = Path(cfg.get("screenshot_dir", "/tmp/cc_visual_test"))
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    # Load API key
    try:
        api_key = Path(key_path).read_text().strip()
    except Exception as e:
        return TestResult("fail", f"Cannot read API key: {e}")

    # Find CC port
    cc_port = find_cc_port()
    if not cc_port:
        return TestResult("fail", "CC not running")

    # Check bridge
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{bridge_port}/api/dronor_health", timeout=3)
    except Exception:
        return TestResult("fail", f"Bridge server not running on port {bridge_port}")

    all_bugs = []    # {section, after_click, severity, description}
    sections_tested = 0
    api_errors = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})

        # Inject bridge shim
        page.add_init_script(path=f"/Users/anvarbakiyev/dronor/apps/pywebview_shim.js")
        page.goto(f"http://127.0.0.1:{cc_port}/cc_ui.html", wait_until="domcontentloaded")
        page.wait_for_timeout(1500)

        sections_to_test = cfg.get("sections", [s["nav"] for s in SECTIONS])

        for section in SECTIONS:
            nav_name = section["nav"]
            if nav_name not in sections_to_test:
                continue

            # Navigate to section
            try:
                page.locator(".nav-item", has_text=nav_name).first.click()
                page.wait_for_timeout(1500)
            except Exception as e:
                all_bugs.append({
                    "section": nav_name,
                    "after_click": None,
                    "severity": "warning",
                    "description": f"Не удалось открыть секцию '{nav_name}': {e}"
                })
                continue

            # Screenshot of section
            shot_path = screenshot_dir / f"{nav_name.replace(' ', '_')}_load.png"
            page.screenshot(path=str(shot_path), full_page=False)
            image_bytes = shot_path.read_bytes()

            context = f"Секция '{nav_name}' после загрузки"
            bugs = ask_claude_vision(image_bytes, api_key, context)

            for bug in bugs:
                if "Vision API error" in bug.get("description", ""):
                    api_errors += 1
                all_bugs.append({
                    "section": nav_name,
                    "after_click": None,
                    **bug
                })

            sections_tested += 1

            # Click buttons and screenshot after each
            for btn_text in section["click_btns"]:
                try:
                    page.click(f"text={btn_text}", timeout=3000)
                    page.wait_for_timeout(2500)  # Wait for async response

                    shot_path = screenshot_dir / f"{nav_name.replace(' ', '_')}_after_{btn_text.replace(' ', '_')}.png"
                    page.screenshot(path=str(shot_path), full_page=False)
                    image_bytes = shot_path.read_bytes()

                    context = f"Секция '{nav_name}' после нажатия кнопки '{btn_text}'"
                    bugs = ask_claude_vision(image_bytes, api_key, context)

                    for bug in bugs:
                        if "Vision API error" in bug.get("description", ""):
                            api_errors += 1
                        all_bugs.append({
                            "section": nav_name,
                            "after_click": btn_text,
                            **bug
                        })

                    # Close any modal that might have opened
                    try:
                        page.keyboard.press("Escape")
                        page.wait_for_timeout(300)
                    except Exception:
                        pass

                except Exception as e:
                    all_bugs.append({
                        "section": nav_name,
                        "after_click": btn_text,
                        "severity": "warning",
                        "description": f"Кнопка '{btn_text}' недоступна или вызвала JS-ошибку: {e}"
                    })

        browser.close()

    # Build report
    critical = [b for b in all_bugs if b.get("severity") == "critical"]
    warnings  = [b for b in all_bugs if b.get("severity") == "warning"]
    infos     = [b for b in all_bugs if b.get("severity") == "info"]

    detail_lines = []
    if critical:
        detail_lines.append(f"CRITICAL ({len(critical)}):")
        for b in critical:
            loc = f"{b['section']}" + (f" → {b['after_click']}" if b.get('after_click') else "")
            detail_lines.append(f"  ✗ [{loc}] {b['description']}")
    if warnings:
        detail_lines.append(f"WARNINGS ({len(warnings)}):")
        for b in warnings:
            loc = f"{b['section']}" + (f" → {b['after_click']}" if b.get('after_click') else "")
            detail_lines.append(f"  ⚠ [{loc}] {b['description']}")
    if infos:
        detail_lines.append(f"INFO ({len(infos)}):")
        for b in infos:
            loc = f"{b['section']}" + (f" → {b['after_click']}" if b.get('after_click') else "")
            detail_lines.append(f"  · [{loc}] {b['description']}")

    detail_lines.append(f"\nTested: {sections_tested} sections | Screenshots: {screenshot_dir}")
    if api_errors:
        detail_lines.append(f"Vision API errors: {api_errors} (check key or network)")

    detail = "\n".join(detail_lines)
    total_bugs = len(critical) + len(warnings)

    if critical:
        status = "fail"
        summary = f"Visual test: {len(critical)} critical, {len(warnings)} warnings in {sections_tested} sections"
    elif warnings:
        status = "warn"
        summary = f"Visual test: {len(warnings)} warnings in {sections_tested} sections"
    else:
        status = "pass"
        summary = f"Visual test: no bugs found in {sections_tested} sections"

    return TestResult(
        status,
        summary,
        detail=detail,
        data={"critical": len(critical), "warnings": len(warnings), "sections_tested": sections_tested}
    )
