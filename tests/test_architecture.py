from pathlib import Path


MAX_PYTHON_LINES = 200
ROOT = Path(__file__).resolve().parents[1]
SCANNED_DIRS = ("eagle_eval", "tests", "examples")


def test_python_files_stay_under_200_lines():
    oversized = []
    for folder in SCANNED_DIRS:
        for path in (ROOT / folder).rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            line_count = len(path.read_text(encoding="utf-8").splitlines())
            if line_count > MAX_PYTHON_LINES:
                oversized.append(f"{path.relative_to(ROOT)}:{line_count}")

    assert not oversized, "Python files above 200 lines:\n" + "\n".join(oversized)
