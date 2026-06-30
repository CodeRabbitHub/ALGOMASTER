"""
AlgoMaster Code Runner
Sandboxed Python executor — receives code + test_cases, runs safely, returns results.
"""
import subprocess
import sys
import json
import textwrap
import tempfile
import os
import time
from flask import Flask, request, jsonify

app = Flask(__name__)

MAX_EXEC_SECS = 10
MAX_OUTPUT_BYTES = 50_000  # 50 KB cap on stdout


def _check_equal(actual, expected_str: str) -> bool:
    """
    Flexible comparison:
    - Try exact string match first
    - Try parsing expected as Python literal and compare values
    - For lists: also try sorted comparison (order-insensitive problems)
    """
    actual_str = str(actual).strip()
    exp = expected_str.strip()

    if actual_str == exp:
        return True

    # Try parsing expected as a Python value
    try:
        exp_val = eval(exp)  # noqa: S307
    except Exception:
        return False

    # Direct equality
    if actual == exp_val:
        return True

    # For lists: sorted comparison (handles problems where order doesn't matter)
    if isinstance(actual, list) and isinstance(exp_val, list):
        try:
            if sorted(str(x) for x in actual) == sorted(str(x) for x in exp_val):
                return True
        except Exception:
            pass

    return False


def _build_test_harness(user_code: str, test_cases: list) -> str:
    """Wrap user code with a test runner."""
    harness = textwrap.dedent(f"""
import sys, json, traceback

# ── User code ──────────────────────────────────────────────────────────────
{user_code}

# ── Comparison helper ───────────────────────────────────────────────────────
def _check_equal(actual, exp_str):
    actual_str = str(actual).strip()
    exp = exp_str.strip()
    if actual_str == exp:
        return True
    try:
        exp_val = eval(exp)
    except Exception:
        return False
    if actual == exp_val:
        return True
    if isinstance(actual, list) and isinstance(exp_val, list):
        try:
            if sorted(str(x) for x in actual) == sorted(str(x) for x in exp_val):
                return True
        except Exception:
            pass
    return False

# ── Test harness ───────────────────────────────────────────────────────────
test_cases = {json.dumps(test_cases)}
results = []

for i, tc in enumerate(test_cases):
    inp = tc.get("input", "")
    expected = tc.get("expected_output", "")
    try:
        # exec input to build local vars (handles "param = value" assignments)
        local_ns = {{}}
        exec(inp, {{}}, local_ns)
        # if exec produced no bindings it was a plain expression — eval it
        if not local_ns:
            local_ns["_arg"] = eval(inp)
        # call solve() with args in insertion order
        if "solve" in dir():
            args = list(local_ns.values())
            actual = solve(*args) if args else solve()
        else:
            actual = eval(inp)
        passed = _check_equal(actual, expected)
        results.append({{
            "test_case": i + 1,
            "passed": passed,
            "input": inp,
            "expected": expected,
            "actual": str(actual),
        }})
    except Exception as e:
        results.append({{
            "test_case": i + 1,
            "passed": False,
            "input": inp,
            "expected": expected,
            "actual": "",
            "error": traceback.format_exc(),
        }})

print("__RESULTS__:" + json.dumps(results))
""")
    return harness


def run_code(code: str, test_cases: list, language: str = "python"):
    """Execute user code in a subprocess with strict timeout."""
    if language != "python":
        return {
            "stdout": "",
            "stderr": "Only Python is supported.",
            "test_results": [],
            "is_correct": False,
            "error_type": "UnsupportedLanguage",
            "error_message": "Only Python is supported.",
            "exec_time_ms": 0,
        }

    # Write to temp file
    harness = _build_test_harness(code, test_cases)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, dir="/tmp"
    ) as f:
        f.write(harness)
        tmp_path = f.name

    start = time.monotonic()
    try:
        proc = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=MAX_EXEC_SECS,
            env={
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "HOME": "/tmp",
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        stdout = proc.stdout[:MAX_OUTPUT_BYTES]
        stderr = proc.stderr[:MAX_OUTPUT_BYTES]

        # Parse structured results if present
        test_results = []
        clean_stdout_lines = []
        for line in stdout.splitlines():
            if line.startswith("__RESULTS__:"):
                try:
                    test_results = json.loads(line[len("__RESULTS__:"):])
                except Exception:
                    pass
            else:
                clean_stdout_lines.append(line)
        clean_stdout = "\n".join(clean_stdout_lines)

        is_correct = bool(test_results) and all(r.get("passed") for r in test_results)

        # Classify error
        error_type = None
        error_message = None
        if proc.returncode != 0 or stderr:
            error_message = stderr.strip()
            if "SyntaxError" in stderr:
                error_type = "SyntaxError"
            elif "NameError" in stderr:
                error_type = "NameError"
            elif "TypeError" in stderr:
                error_type = "TypeError"
            elif "IndexError" in stderr or "KeyError" in stderr:
                error_type = "IndexError/KeyError"
            elif "RecursionError" in stderr:
                error_type = "RecursionError"
            elif "MemoryError" in stderr:
                error_type = "MemoryError"
            else:
                error_type = "RuntimeError"

        return {
            "stdout": clean_stdout,
            "stderr": stderr,
            "test_results": test_results,
            "is_correct": is_correct,
            "error_type": error_type,
            "error_message": error_message,
            "exec_time_ms": elapsed_ms,
        }

    except subprocess.TimeoutExpired:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return {
            "stdout": "",
            "stderr": f"Time limit exceeded ({MAX_EXEC_SECS}s)",
            "test_results": [],
            "is_correct": False,
            "error_type": "TimeLimitExceeded",
            "error_message": f"Your code exceeded the {MAX_EXEC_SECS}s time limit.",
            "exec_time_ms": elapsed_ms,
        }
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/execute", methods=["POST"])
def execute():
    data = request.get_json(force=True, silent=True) or {}
    code = data.get("code", "")
    test_cases = data.get("test_cases", [])
    language = data.get("language", "python")

    if not code.strip():
        return jsonify({
            "stdout": "",
            "stderr": "No code provided.",
            "test_results": [],
            "is_correct": False,
            "error_type": "EmptyCode",
            "error_message": "No code provided.",
            "exec_time_ms": 0,
        }), 400

    result = run_code(code, test_cases, language)
    status = 200 if result["error_type"] is None else 200  # always 200; caller checks is_correct
    return jsonify(result), status


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
