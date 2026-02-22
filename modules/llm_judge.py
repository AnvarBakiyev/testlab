"""
modules/llm_judge.py — LLM-as-judge for UX quality.
config: texts or source_expert, rubric, threshold=0.75, sample_size=10
"""
import json
import requests
from core.base import TestResult

PROMPT = """Оцени уведомление AI-ассистента. Контекст: {rubric}

Уведомление:
{text}

Оцени по 4 критериям (1-4 балла):
1. Ясность — сразу понятно что произошло?
2. Действенность — понятно что делать?
3. Тон — человечный, не машинный?
4. Чистота — нет JSON/скобок/snake_case/UUID?

Ответь ТОЛЬКО JSON без markdown:
{{"clarity": int, "actionability": int, "tone": int, "cleanliness": int, "reason": "кратко"}}"""

def run(config: dict) -> TestResult:
    texts = _collect(config)
    if not texts:
        return TestResult(status="warn", msg="Нет текстов для LLM-judge")
    sample = texts[:config.get("sample_size", 10)]
    rubric = config.get("rubric", "Уведомления персонального AI-ассистента")
    threshold = config.get("threshold", 0.75)
    url = config.get("dronor_url", "http://localhost:9100")
    scores = []
    failures = []
    for i, text in enumerate(sample):
        r = _judge(text, rubric, url)
        if r is None:
            continue
        norm = r["total"] / 16
        scores.append(norm)
        if norm < threshold:
            failures.append(f"[{i}] score={norm:.2f}: {r.get('reason','')[:80]}")
    if not scores:
        return TestResult(status="warn", msg="LLM-judge не смог оценить тексты")
    avg = sum(scores) / len(scores)
    data = {"avg": round(avg, 3), "n": len(scores), "threshold": threshold}
    if avg < threshold:
        return TestResult(status="fail",
                          msg=f"LLM-judge avg={avg:.2f} < {threshold}",
                          detail="
".join(failures[:3]), data=data)
    if failures:
        return TestResult(status="warn",
                          msg=f"LLM-judge avg={avg:.2f}, {len(failures)} ниже порога",
                          data=data)
    return TestResult(status="pass", msg=f"LLM-judge avg={avg:.2f} ({len(scores)} текстов)",
                      data=data)

def _judge(text, rubric, url):
    prompt = PROMPT.format(rubric=rubric, text=text[:500])
    try:
        resp = requests.post(f"{url}/api/expert/run",
                             json={"expert_name": "claude_judge",
                                   "params": {"prompt": prompt}},
                             timeout=20).json()
        raw = resp.get("result", {})
        if isinstance(raw, str):
            raw = json.loads(raw)
        total = sum(raw.get(k, 0) for k in ("clarity","actionability","tone","cleanliness"))
        return {**raw, "total": total}
    except Exception:
        return None

def _collect(config):
    if "texts" in config:
        return config["texts"]
    if "source_expert" in config:
        try:
            resp = requests.post(
                f"{config.get('dronor_url','http://localhost:9100')}/api/expert/run",
                json={"expert_name": config["source_expert"],
                      "params": config.get("source_expert_params", {})},
                timeout=15).json()
            data = resp.get("result", {})
            return data.get("texts", []) if isinstance(data, dict) else []
        except Exception:
            return []
    return []
