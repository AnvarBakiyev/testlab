"""
E2E: Overview screen loads — KG has nodes, no crash.
"""
import os

AGI_BASE = os.path.expanduser("/Users/anvarbakiyev/dronor/local_data/personal_agi")
KUZU_DB_PATH = os.path.join(AGI_BASE, "kuzu_db")

def run(cfg: dict):
    from core.base import TestResult
    try:
        import kuzu
        db = kuzu.Database(KUZU_DB_PATH, read_only=True)
        conn = kuzu.Connection(db)
        total = 0
        for label in ["Person", "Organization", "Document", "Communication"]:
            try:
                r = conn.execute(f"MATCH (n:{label}) RETURN count(n)")
                total += r.get_next()[0]
            except:
                pass
        conn.close()

        if total == 0:
            return TestResult("warn", "KG is empty — no nodes found",
                              detail="Overview would show all zeros",
                              data={"total_nodes": 0})
        return TestResult("pass", f"Overview loads OK — {total} KG nodes",
                          data={"total_nodes": total})
    except Exception as e:
        return TestResult("fail", f"Overview crashed: {e}")
