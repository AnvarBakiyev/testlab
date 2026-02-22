# Universal TestLab

Platform for testing AI-agent projects. One contract, any project.

## Philosophy

- **One interface**: every module returns `TestResult(status, msg, detail, data)`
- **Dronor-native**: any Dronor expert becomes a test via `dronor_expert` module
- **Config-driven**: adding a project = one JSON file, zero Python code required
- **Wiki-first**: results auto-generate wiki pages for Command Center

## Structure

```
core/           Runner, Reporter, Wiki, GitHub pusher
modules/        Reusable test modules (one responsibility each)
projects/       Per-project configs (project.json)
wiki/           Auto-generated docs (synced to Command Center)
results/        Test run history (JSON, git-tracked)
```

## Adding a new project

1. Create `projects/{id}/project.json` (copy personal_agi as template)
2. Add entry to `projects.json`
3. Done — TestLab discovers it automatically

## Writing a new test module

```python
# modules/my_check.py
from core.base import TestResult

def run(config: dict) -> TestResult:
    # your logic here
    return TestResult(status="pass", msg="All good")
```

One function. One contract. That's the entire API.

## Using Dronor experts as tests

No Python code needed — just config:

```json
{
  "module": "dronor_expert",
  "config": {
    "expert": "my_expert_name",
    "params": {"key": "value"},
    "expect": {"status": "success"}
  }
}
```
