"""
modules/text_quality.py — Detect LLM artifacts in user-visible text.

Config options:
  texts: list[str]           — hardcoded test strings (for unit tests)
  db: str                    — path relative to base_path to SQLite DB
  query: str                 — SQL query returning text rows (first column used)
  min_rows: int              — minimum expected rows from DB (default 1)
  check_artifacts: bool      — check for snake_case, markdown, etc (default True)
"""
import sqlite3
import re
from pathlib import Path
from core.base import TestResult


ARTIFACT_PATTERNS = [
    (r'\b[a-z]+_[a-z_]+\b', 'snake_case'),
    (r'^#{1,4} ', 'markdown_header'),
    (r'\*\*[^*]+\*\*', 'bold_markdown'),
    (r'^\s*[-*]\s', 'bullet_point'),
    (r'```', 'code_block'),
]


def has_artifact(text: str) -> tuple[bool, str]:
    for pattern, name in ARTIFACT_PATTERNS:
        if re.search(pattern, text, re.MULTILINE):
            return True, name
    return False, ''


def run(config: dict) -> TestResult:
    base = Path(config.get('_base_path', '/'))
    texts = config.get('texts', [])

    # Load from DB if configured
    if 'db' in config and 'query' in config:
        try:
            conn = sqlite3.connect(str(base / config['db']))
            rows = conn.execute(config['query']).fetchall()
            conn.close()
            texts = [row[0] for row in rows if row[0]]
        except Exception as e:
            return TestResult(status='fail', msg=f'DB error: {e}')

        min_rows = config.get('min_rows', 1)
        if len(texts) < min_rows:
            return TestResult(
                status='warn',
                msg=f'Только {len(texts)} строк в БД (ожидалось {min_rows}+)',
            )

    if not texts:
        return TestResult(status='warn', msg='Нет текстов для проверки')

    if not config.get('check_artifacts', True):
        return TestResult(status='pass', msg=f'{len(texts)} текстов проверено (артефакты отключены)')

    bad = []
    for text in texts:
        found, artifact_type = has_artifact(text)
        if found:
            bad.append((text[:60], artifact_type))

    if bad:
        examples = '; '.join(f'{t!r}({a})' for t, a in bad[:3])
        return TestResult(
            status='fail',
            msg=f'{len(bad)} texts with artifacts out of {len(texts)}',
            detail=examples,
            data={'total': len(texts), 'with_artifacts': len(bad), 'examples': bad[:5]},
        )

    return TestResult(
        status='pass',
        msg=f'Все {len(texts)} текстов чисты',
        data={'total': len(texts)},
    )
