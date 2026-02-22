"""
modules/llm_judge.py -- LLM-as-judge for UX quality.

config:
  texts         list of strings to evaluate (or use source_expert)
  source_expert Dronor expert name that returns {texts: [...]}
  rubric        str  -- context for the judge
  threshold     float 0..1, default 0.75
  sample_size   int, default 10
  judge_expert  str  -- Dronor expert that accepts {prompt} and returns scored JSON
                        default: None (module returns warn if not configured)
  dronor_url    str, default http://localhost:9100

Why judge_expert has no default:
  Scaffold must not assume any specific expert exists on the target machine.
  Set judge_expert in project.json once you have a working LLM expert.
"""
import json
import requests
from core.base import TestResult

JUDGE_PROMPT = """Evaluate this AI assistant notification. Context: {rubric}

Notification:
{text}

Score on 4 criteria (1-4 each):
1. Clarity      -- is it immediately clear what happened?
2. Actionability -- is it clear what to do?
3. Tone         -- human, not robotic?
4. Cleanliness  -- no JSON / snake_case / UUIDs leaking through?

Respond ONLY with JSON, no markdown:
{{"clarity": int, "actionability": int, "tone": int, "cleanliness": int, "reason": "brief"}}"""


def run(config: dict) -> TestResult:
    judge_expert = config.get("judge_expert")
    if not judge_expert:
        return TestResult(
            status="warn",
            msg="llm_judge: judge_expert not configured -- skipping",
            detail="Set 'judge_expert' in project.json suite config to enable LLM scoring.",
        )

    texts = _collect(config)
    if not texts:
        return TestResult(status="warn", msg="llm_judge: no texts to evaluate")

    sample = texts[: config.get("sample_size", 10)]
    rubric = config.get("rubric", "Personal AI assistant notifications")
    threshold = config.get("threshold", 0.75)
    url = config.get("dronor_url", "http://localhost:9100")

    scores = []
    failures = []
    for i, text in enumerate(sample):
        scored = _judge(text, rubric, url, judge_expert)
        if scored is None:
            continue
        norm = scored["total"] / 16
        scores.append(norm)
        if norm < threshold:
            failures.append(f"[{i}] score={norm:.2f}: {scored.get('reason', '')[:80]}")

    if not scores:
        return TestResult(status="warn", msg="llm_judge: judge returned no scores")

    avg = sum(scores) / len(scores)
    data = {"avg": round(avg, 3), "n": len(scores), "threshold": threshold}

    if avg < threshold:
        return TestResult(
            status="fail",
            msg=f"llm_judge avg={avg:.2f} < {threshold}",
            detail="\n".join(failures[:3]),
            data=data,
        )
    if failures:
        return TestResult(
            status="warn",
            msg=f"llm_judge avg={avg:.2f}, {len(failures)} below threshold",
            data=data,
        )
    return TestResult(
        status="pass",
        msg=f"llm_judge avg={avg:.2f} ({len(scores)} texts)",
        data=data,
    )


def _judge(text: str, rubric: str, url: str, judge_expert: str) -> dict | None:
    prompt = JUDGE_PROMPT.format(rubric=rubric, text=text[:500])
    try:
        resp = requests.post(
            f"{url}/api/expert/run",
            json={"expert_name": judge_expert, "params": {"prompt": prompt}},
            timeout=20,
        ).json()
        raw = resp.get("result", {})
        if isinstance(raw, str):
            raw = json.loads(raw)
        if not isinstance(raw, dict):
            return None
        total = sum(raw.get(k, 0) for k in ("clarity", "actionability", "tone", "cleanliness"))
        return {**raw, "total": total}
    except Exception:
        return None


def _collect(config: dict) -> list:
    if "texts" in config:
        return config["texts"]
    if "source_expert" in config:
        url = config.get("dronor_url", "http://localhost:9100")
        try:
            resp = requests.post(
                f"{url}/api/expert/run",
                json={"expert_name": config["source_expert"],
                      "params": config.get("source_expert_params", {})},
                timeout=15,
            ).json()
            data = resp.get("result", {})
            return data.get("texts", []) if isinstance(data, dict) else []
        except Exception:
            return []
    return []
