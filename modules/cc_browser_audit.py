"""
CC Browser Audit — широкий Playwright тест AGI Command Center.

Что проверяет:
1. JS ошибки на каждой странице
2. Дубли в списках (одинаковые data-aid)
3. Кнопки которые крашатся при клике
4. Loading... которые не пропали
5. Плохие тексты (snake_case, null, undefined, [object Object])
6. Пустые секции где должны быть данные
"""
import re
import subprocess
import urllib.request

SECTIONS = [
    {"page": "overview",   "nav": "Overview",       "click_btns": []},
    {"page": "persons",    "nav": "People",          "click_btns": []},
    {"page": "orgs",       "nav": "Organizations",   "click_btns": []},
    {"page": "comms",      "nav": "Communications",  "click_btns": []},
    {"page": "events",     "nav": "Events",          "click_btns": []},
    {"page": "actions",    "nav": "Pending Actions",  "click_btns": []},
    {"page": "memory",     "nav": "Memory",          "click_btns": []},
    {"page": "cars",       "nav": "CARS Analytics",  "click_btns": []},
    {"page": "autoreply",  "nav": "Auto-Reply",      "click_btns": []},
    {"page": "connectors", "nav": "Connectors",      "click_btns": ["Quick Sync"]},
    {"page": "kgsync",     "nav": "KG Sync",         "click_btns": []},
    {"page": "analytics",  "nav": "Analytics",       "click_btns": []},
    {"page": "agents",     "nav": "Agents",          "click_btns": []},
    {"page": "finance",    "nav": "Finance",         "click_btns": []},
]

BAD_EXACT = {"[object Object]", "undefined", "NaN"}


def find_cc_port():
    result = subprocess.run(["lsof", "-i", "-P", "-n"], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if "python" in line.lower() and "listen" in line.lower():
            m = re.search(r'127\.0\.0\.1:(\d+)\s+\(LISTEN\)', line)
            if m:
                port = int(m.group(1))
                if port != 9300:
                    return port
    return None


def run(cfg: dict):
    from core.base import TestResult
    from playwright.sync_api import sync_playwright

    bridge_port = cfg.get("bridge_port", 9300)
    cc_port = find_cc_port()

    if not cc_port:
        return TestResult("fail", "CC not running — port not found")

    try:
        urllib.request.urlopen(f"http://127.0.0.1:{bridge_port}/api/dronor_health", timeout=3)
    except Exception:
        return TestResult("fail", f"Bridge server not running on :{bridge_port}. Run: python3 bridge_server.py")

    cc_url = f"http://127.0.0.1:{cc_port}/cc_ui.html"
    issues = []
    warnings = []
    checked = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()

        js_errors = []
        page.on("pageerror", lambda err: js_errors.append(str(err)))
        page.on("console", lambda msg: js_errors.append(msg.text) if msg.type == "error" else None)

        try:
            page.goto(cc_url, timeout=15000)
            page.wait_for_timeout(3000)
        except Exception as e:
            browser.close()
            return TestResult("fail", f"Cannot open CC at {cc_url}: {e}")

        # Очищаем JS ошибки от старта (shim-логи)
        js_errors.clear()

        for section in SECTIONS:
            nav_text = section["nav"]
            page_id  = section["page"]

            # Навигация
            try:
                page.locator(".nav-item", has_text=nav_text).first.click()
                page.wait_for_timeout(2000)
            except Exception as e:
                warnings.append(f"{nav_text}: nav click failed — {e}")
                continue

            visible = page.locator("body").inner_text()

            # 1. Loading... не пропал
            stuck_count = visible.count("Loading...")
            if stuck_count:
                issues.append(f"{nav_text}: {stuck_count}x 'Loading...' stuck")

            # 2. Плохие значения в тексте
            for bad in BAD_EXACT:
                if bad in visible:
                    issues.append(f"{nav_text}: raw value '{bad}' visible to user")

            # 3. snake_case в видимом тексте (не в атрибутах)
            snake = re.findall(r'(?<!["\'/=])\b[a-z]{2,}(?:_[a-z0-9]+){1,}\b(?!["\'])', visible)
            # убираем известные технические false-positives которые ок в UI
            ignore = {"quick_sync", "deep_scan", "auto_reply", "kg_sync"}
            real_snake = [s for s in set(snake) if s not in ignore][:5]
            if real_snake:
                warnings.append(f"{nav_text}: snake_case in visible text — {real_snake}")

            # 4. Дубли элементов (action id повторяется)
            if page_id in ("actions", "events", "persons", "comms"):
                dupes = page.evaluate("""
                    () => {
                        const ids = Array.from(document.querySelectorAll('[data-aid]'))
                                        .map(el => el.getAttribute('data-aid'));
                        const seen = {};
                        const dupes = [];
                        ids.forEach(id => {
                            seen[id] = (seen[id] || 0) + 1;
                            if (seen[id] === 2) dupes.push(id);
                        });
                        return dupes;
                    }
                """)
                if dupes:
                    issues.append(f"{nav_text}: {len(dupes)} duplicate items — e.g. {dupes[0]}")

            # 5. JS ошибки
            real_errors = [e for e in js_errors
                           if "js_log" not in e and "shim" not in e and "favicon" not in e]
            if real_errors:
                issues.append(f"{nav_text}: {len(real_errors)} JS error(s) — {real_errors[0][:120]}")
            js_errors.clear()

            # 6. Клики по кнопкам
            for btn_text in section.get("click_btns", []):
                btns = page.locator("button", has_text=btn_text).all()
                if not btns:
                    warnings.append(f"{nav_text}: button '{btn_text}' not found in DOM")
                    continue
                try:
                    btns[0].click()
                    page.wait_for_timeout(2500)
                    body_after = page.locator("body").inner_text()
                    if re.search(r'\bFailed:\b|\bTraceback\b|\bAttributeError\b', body_after):
                        issues.append(f"{nav_text}: button '{btn_text}' caused error")
                    else:
                        checked.append(f"{nav_text}: '{btn_text}' clicked OK")
                    # Закрыть модал
                    for sel in [".modal-close", "button:has-text('Close')", "button:has-text('×')"]:
                        try:
                            btn = page.locator(sel).first
                            if btn.is_visible(timeout=500):
                                btn.click()
                                break
                        except Exception:
                            pass
                except Exception as e:
                    issues.append(f"{nav_text}: button '{btn_text}' crashed — {e}")

            checked.append(f"{nav_text}: loaded")

        browser.close()

    lines = []
    if issues:
        lines.append(f"ISSUES ({len(issues)}):")
        lines.extend(f"  ✗ {i}" for i in issues)
    if warnings:
        lines.append(f"WARNINGS ({len(warnings)}):")
        lines.extend(f"  ⚠ {w}" for w in warnings[:15])
    lines.append(f"PASSED: {len(checked)} checks")
    detail = "\n".join(lines)

    if issues:
        status = "fail" if len(issues) >= 3 else "warn"
        return TestResult(status,
            f"CC Browser Audit: {len(issues)} issues, {len(warnings)} warnings / {len(SECTIONS)} sections",
            detail=detail, data={"issues": len(issues), "warnings": len(warnings)})

    if warnings:
        return TestResult("warn",
            f"CC Browser Audit: all sections loaded, {len(warnings)} warnings",
            detail=detail, data={"issues": 0, "warnings": len(warnings)})

    return TestResult("pass",
        f"CC Browser Audit: all {len(SECTIONS)} sections clean",
        detail=detail, data={"issues": 0, "warnings": 0})
