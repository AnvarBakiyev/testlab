"""
CC Visual Tester v2 — Playwright + Claude Vision.

Стратегия:
- 3 скриншота на секцию: верх, середина (после скролла), низ страницы
- 5 секунд ожидания после навигации (данные должны загрузиться)
- Connectors: каждый Deep Scan по очереди, ждём завершения, закрываем модал
- Каждый скриншот анализирует Claude Vision отдельно

config:
  bridge_port: 9300
  anthropic_key_path: /Users/anvarbakiyev/Desktop/credentials/anthropic_api_key.txt
  screenshot_dir: /tmp/cc_visual_test
"""
import base64
import json
import re
import urllib.request
from pathlib import Path


SECTIONS = [
    {"nav": "Overview",        "mode": "scroll_only"},
    {"nav": "People",          "mode": "scroll_only"},
    {"nav": "Organizations",   "mode": "scroll_only"},
    {"nav": "Pending Actions", "mode": "scroll_only"},
    {"nav": "Memory",          "mode": "scroll_only"},
    {"nav": "CARS Analytics",  "mode": "scroll_only"},
    {"nav": "Auto-Reply",      "mode": "scroll_only"},
    {"nav": "Connectors",      "mode": "deep_scan_all"},
    {"nav": "KG Sync",         "mode": "scroll_only"},
    {"nav": "Analytics",       "mode": "scroll_only"},
]

VISION_PROMPT = """Ты QA-инженер. Анализируй скриншот интерфейса AGI Command Center.

Найди ТОЛЬКО реальные проблемы:
- Дублирующиеся строки (один и тот же элемент показан дважды и более)
- Текст ошибок (красные сообщения, Error:, Exception:, failed, traceback)
- Технические идентификаторы видимые пользователю (snake_case, uuid, None, undefined, null)
- Застрявшие индикаторы загрузки (Loading..., spinner без данных)
- Пустые секции где явно должны быть данные
- Сырой JSON или XML виден напрямую пользователю
- Кнопки или элементы в неправильном состоянии

Формат ответа — строго JSON:
{"bugs": [{"severity": "critical|warning|info", "description": "конкретное описание на русском"}]}

Если проблем нет — {"bugs": []}
ТОЛЬКО JSON, никакого другого текста."""


def find_cc_port():
    candidates = list(range(60000, 60300)) + list(range(49152, 49300)) + list(range(50000, 50200))
    for port in candidates:
        if port in (9300, 9200, 9100):
            continue
        try:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/cc_ui.html", timeout=0.3)
            if resp.status == 200:
                return port
        except Exception:
            continue
    return None


def ask_claude_vision(image_bytes, api_key, context):
    image_b64 = base64.standard_b64encode(image_bytes).decode()
    payload = {
        "model": "claude-opus-4-5",
        "max_tokens": 1024,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_b64}},
                {"type": "text", "text": VISION_PROMPT + f"\n\nКонтекст: {context}"}
            ]
        }]
    }
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        text = data["content"][0]["text"].strip()
        text = re.sub(r'^```[a-z]*\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        return json.loads(text).get("bugs", [])
    except Exception as e:
        return [{"severity": "info", "description": f"Vision API error: {e}"}]


def scroll_and_screenshot(page, shot_dir, name_prefix, api_key, section_name):
    bugs = []
    total_height = page.evaluate(
        "document.querySelector('.content') ? document.querySelector('.content').scrollHeight : document.body.scrollHeight"
    ) or 900
    scroll_positions = [0, total_height // 2, max(0, total_height - 900)]
    labels = ["top", "middle", "bottom"]

    for i, scroll_y in enumerate(scroll_positions):
        page.evaluate(f"document.querySelector('.content').scrollTop = {scroll_y}")
        page.wait_for_timeout(800)
        shot_path = shot_dir / f"{name_prefix}_{i+1}_{labels[i]}.png"
        page.screenshot(path=str(shot_path), full_page=False)
        context = f"Секция '{section_name}', скролл: {labels[i]} (y={scroll_y}px)"
        bugs.extend(ask_claude_vision(shot_path.read_bytes(), api_key, context))

    # Reset scroll
    page.evaluate("document.querySelector('.content').scrollTop = 0")
    return bugs


def close_modal(page):
    try:
        btn = page.locator("button:has-text('Close'), button:has-text('Закрыть'), .modal-close").first
        if btn.is_visible(timeout=500):
            btn.click()
            page.wait_for_timeout(500)
            return
    except Exception:
        pass
    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
    except Exception:
        pass


def run_deep_scans(page, shot_dir, api_key):
    bugs = []

    # Initial screenshot
    shot_path = shot_dir / "Connectors_1_initial.png"
    page.screenshot(path=str(shot_path), full_page=False)
    bugs.extend(ask_claude_vision(shot_path.read_bytes(), api_key, "Connectors: начальное состояние"))

    # Scroll down to see all connectors
    page.evaluate("document.querySelector('.content').scrollTop = 500")
    page.wait_for_timeout(600)
    shot_path = shot_dir / "Connectors_2_scrolled.png"
    page.screenshot(path=str(shot_path), full_page=False)
    bugs.extend(ask_claude_vision(shot_path.read_bytes(), api_key, "Connectors: список коннекторов (прокрутка вниз)"))

    # Reset scroll
    page.evaluate("document.querySelector('.content').scrollTop = 0")
    page.wait_for_timeout(400)

    # Click each Deep Scan button
    deep_btns = page.locator("button:has-text('Deep Scan')").all()
    total = len(deep_btns)

    for idx in range(total):
        btns = page.locator("button:has-text('Deep Scan')").all()
        if idx >= len(btns):
            break
        btn = btns[idx]
        btn_id = btn.get_attribute("id") or ""
        label = btn_id.replace("cb-d-", "").replace("_", " ").title() if "cb-d-" in btn_id else f"#{idx+1}"

        try:
            if not btn.is_visible(timeout=500):
                btn.scroll_into_view_if_needed()
                page.wait_for_timeout(300)
            btn.scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            btn.click()
            page.wait_for_timeout(1000)

            # Screenshot modal
            shot_path = shot_dir / f"Connectors_deep_{idx+1}_{label.replace(' ', '_')}_modal.png"
            page.screenshot(path=str(shot_path), full_page=False)
            bugs.extend(ask_claude_vision(shot_path.read_bytes(), api_key,
                         f"Connectors: Deep Scan '{label}' — модал открыт"))

            # Wait for completion (max 10s)
            for _ in range(20):
                page.wait_for_timeout(500)
                try:
                    if page.locator("text=Completed").is_visible(timeout=100):
                        break
                    if page.locator("text=Error").is_visible(timeout=100):
                        break
                except Exception:
                    pass

            # Screenshot result
            shot_path = shot_dir / f"Connectors_deep_{idx+1}_{label.replace(' ', '_')}_result.png"
            page.screenshot(path=str(shot_path), full_page=False)
            bugs.extend(ask_claude_vision(shot_path.read_bytes(), api_key,
                         f"Connectors: Deep Scan '{label}' — результат"))

            close_modal(page)
            page.wait_for_timeout(800)

        except Exception as e:
            bugs.append({"severity": "warning",
                         "description": f"Deep Scan '{label}': ошибка — {e}"})

    return bugs


def run(cfg):
    from core.base import TestResult
    from playwright.sync_api import sync_playwright

    bridge_port = cfg.get("bridge_port", 9300)
    key_path = cfg.get("anthropic_key_path", "/Users/anvarbakiyev/Desktop/credentials/anthropic_api_key.txt")
    screenshot_dir = Path(cfg.get("screenshot_dir", "/tmp/cc_visual_test"))
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    try:
        api_key = Path(key_path).read_text().strip()
    except Exception as e:
        return TestResult("fail", f"Cannot read API key: {e}")

    cc_port = find_cc_port()
    if not cc_port:
        return TestResult("fail", "CC not running")

    try:
        urllib.request.urlopen(f"http://127.0.0.1:{bridge_port}/api/dronor_health", timeout=3)
    except Exception:
        return TestResult("fail", f"Bridge not running on port {bridge_port}")

    all_bugs = []
    sections_tested = 0
    api_errors = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.goto(f"http://127.0.0.1:{cc_port}/cc_ui.html", wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        sections_to_test = cfg.get("sections", [s["nav"] for s in SECTIONS])

        for section in SECTIONS:
            nav_name = section["nav"]
            if nav_name not in sections_to_test:
                continue

            try:
                page.locator(".nav-item", has_text=nav_name).first.click()
                page.wait_for_timeout(5000)
            except Exception as e:
                all_bugs.append({"section": nav_name, "severity": "warning",
                                  "description": f"Не удалось открыть секцию: {e}"})
                continue

            sections_tested += 1
            prefix = nav_name.replace(" ", "_")

            if section["mode"] == "deep_scan_all":
                bugs = run_deep_scans(page, screenshot_dir, api_key)
            else:
                bugs = scroll_and_screenshot(page, screenshot_dir, prefix, api_key, nav_name)

            for bug in bugs:
                if "Vision API error" in bug.get("description", ""):
                    api_errors += 1
                all_bugs.append({"section": nav_name, **bug})

        browser.close()

    critical = [b for b in all_bugs if b.get("severity") == "critical"]
    warnings  = [b for b in all_bugs if b.get("severity") == "warning"]
    infos     = [b for b in all_bugs if b.get("severity") == "info"]

    lines = []
    if critical:
        lines.append(f"CRITICAL ({len(critical)}):")
        for b in critical:
            lines.append(f"  \u2717 [{b['section']}] {b['description']}")
    if warnings:
        lines.append(f"WARNINGS ({len(warnings)}):")
        for b in warnings:
            lines.append(f"  \u26a0 [{b['section']}] {b['description']}")
    if infos:
        lines.append(f"INFO ({len(infos)}):")
        for b in infos:
            lines.append(f"  \u00b7 [{b['section']}] {b['description']}")

    lines.append(f"\nTested: {sections_tested} sections | Screenshots: {screenshot_dir}")
    if api_errors:
        lines.append(f"Vision API errors: {api_errors}")

    detail = "\n".join(lines)
    msg = f"Visual test v2: {len(critical)} critical, {len(warnings)} warnings in {sections_tested} sections"

    if critical:
        status = "fail"
    elif warnings:
        status = "warn"
    else:
        status = "pass"

    return TestResult(status, msg, detail=detail,
                      data={"critical": len(critical), "warnings": len(warnings), "sections_tested": sections_tested})
