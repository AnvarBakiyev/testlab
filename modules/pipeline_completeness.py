"""
modules/pipeline_completeness.py — Silent pipeline failure detection.
config: input_db, input_query, output_db, output_query, tolerance_percent=10
"""
import sqlite3
from pathlib import Path
from core.base import TestResult

def run(config: dict) -> TestResult:
    base = Path(config.get("_base_path", "/"))
    try:
        in_conn = sqlite3.connect(str(base / config["input_db"]))
        input_count = in_conn.execute(config["input_query"]).fetchone()[0]
        in_conn.close()
        out_conn = sqlite3.connect(str(base / config["output_db"]))
        output_count = out_conn.execute(config["output_query"]).fetchone()[0]
        out_conn.close()
    except Exception as e:
        return TestResult(status="fail", msg=f"DB error: {e}")
    if input_count == 0:
        return TestResult(status="warn", msg="Входных записей нет (простой?)")
    tolerance = config.get("tolerance_percent", 10)
    dropped = input_count - output_count
    drop_pct = dropped / input_count * 100
    min_expected = int(input_count * (1 - tolerance / 100))
    if output_count < min_expected:
        return TestResult(
            status="fail",
            msg=f"SILENT FAILURE: потеряно {dropped} записей ({drop_pct:.1f}%)",
            detail=f"input={input_count} output={output_count} tolerance={tolerance}%",
            data={"input": input_count, "output": output_count, "dropped": dropped},
        )
    if dropped > 0:
        return TestResult(status="warn",
                          msg=f"Потеряно {dropped} ({drop_pct:.1f}%) — в норме",
                          data={"input": input_count, "output": output_count})
    return TestResult(status="pass", msg=f"Все {input_count} записей обработаны",
                      data={"input": input_count, "output": output_count})
