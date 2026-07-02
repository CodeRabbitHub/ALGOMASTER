"""
AlgoMaster Code Runner
Sandboxed Python executor — receives code + test_cases, runs safely, returns results.

Security note on the grading harness (see _build_test_harness):
  User-submitted code and the grading loop necessarily run in the same
  Python process (there is no per-submission sandbox beyond the container
  itself). Two protections keep a submission from forging a passing result:

  1. The harness's real results line is prefixed with a per-run, randomly
     generated marker that is *never* exposed to the user's code before the
     harness computes it. A submission cannot predict or reproduce this
     marker, so anything it prints under the old fixed "__RESULTS__:" prefix
     is simply ignored by the parser.
  2. The user's code is executed inside a try/except that swallows
     SystemExit/KeyboardInterrupt and captures any other exception, so a
     submission calling sys.exit() (or raising) can never prevent the
     harness's own grading loop from running afterward. (A hard os._exit()
     still terminates the process, but with no valid marker in stdout the
     run correctly grades as failed rather than falsely passing — the
     scorer fails closed, not open.)
"""
import subprocess
import sys
import json
import textwrap
import tempfile
import os
import time
import uuid
import resource
from flask import Flask, request, jsonify

app = Flask(__name__)

DEFAULT_MAX_EXEC_SECS = 10
DEFAULT_MAX_MEMORY_MB = 128
MAX_OUTPUT_BYTES = 50_000  # 50 KB cap on stdout

MAX_EXEC_SECS = int(os.environ.get("MAX_EXECUTION_TIME", DEFAULT_MAX_EXEC_SECS))
MAX_MEMORY_MB = int(os.environ.get("MAX_MEMORY_MB", DEFAULT_MAX_MEMORY_MB))


def _limit_resources():
    """
    preexec_fn for the submitted-code subprocess: caps virtual memory and CPU
    time at the OS level (in addition to the wall-clock timeout enforced via
    subprocess.communicate(timeout=...)). Runs in the forked child before
    exec, so these limits apply only to the user-code process, not the
    Flask/gunicorn server itself.
    """
    mem_bytes = MAX_MEMORY_MB * 1024 * 1024
    try:
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
    except (ValueError, OSError):
        pass  # platform doesn't support RLIMIT_AS (e.g. some macOS setups) — timeout still applies
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (MAX_EXEC_SECS, MAX_EXEC_SECS))
    except (ValueError, OSError):
        pass


def _build_test_harness(user_code: str, test_cases: list, marker: str) -> str:
    """Wrap user code with a test runner.

    `marker` is a per-run random token that the harness's genuine results
    line is prefixed with; user code has no way to discover it before the
    harness computes it, so it cannot forge a matching output line.
    """
    indented_user_code = textwrap.indent(user_code, "    ") or "    pass"
    harness = f"""
import sys, json, traceback, types as _types

_HARNESS_BUILTINS = {{'_check_equal', '_types', '_user_code_error'}}

# ── User code runs in a guarded scope ───────────────────────────────────────
# SystemExit/KeyboardInterrupt from the submission are swallowed so it can
# never prevent the grading loop below from running. Any other exception
# raised while defining the submission is captured and surfaced per test
# case instead of crashing the whole run.
_user_code_error = None
try:
{indented_user_code}
except (SystemExit, KeyboardInterrupt):
    pass
except BaseException:
    _user_code_error = traceback.format_exc()

# ── Find the user's entry-point function ────────────────────────────────────
# Prefer a conventionally-named function (solve/solution) if present, since
# users often define helper functions first. Otherwise fall back to the
# LAST function defined in source order (typically the main solution, since
# helpers are usually written before the function that uses them) rather
# than the first.
_user_funcs = [
    name for name, val in list(globals().items())
    if isinstance(val, _types.FunctionType)
    and not name.startswith('_')
    and name not in _HARNESS_BUILTINS
]
_preferred = [n for n in _user_funcs if n in ('solve', 'solution')]
if _preferred:
    _solve_fn = globals()[_preferred[0]]
elif _user_funcs:
    _solve_fn = globals()[_user_funcs[-1]]
else:
    _solve_fn = None

# ── Comparison helper ───────────────────────────────────────────────────────
_FLOAT_TOL = 1e-5  # matches LeetCode's accepted precision for float answers

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
    # Float tolerance: accept answers within 1e-5 of expected (LeetCode standard)
    if isinstance(actual, (int, float)) and isinstance(exp_val, (int, float)):
        if abs(float(actual) - float(exp_val)) <= _FLOAT_TOL:
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
    if _solve_fn is None and _user_code_error is not None:
        results.append({{
            "test_case": i + 1,
            "passed": False,
            "input": inp,
            "expected": expected,
            "actual": "",
            "error": _user_code_error,
        }})
        continue
    try:
        # exec input to build local vars (handles "param = value" assignments)
        local_ns = {{}}
        try:
            exec(inp, {{}}, local_ns)
        except SyntaxError:
            # LeetCode-style: "nums = [1,2], k = 4" — comma-joined assignments
            # that are not valid Python as a single statement. Split on commas
            # that are immediately followed by a bare name and "=".
            import re as _re
            for _part in _re.split(r',\s*(?=\w+\s*=)', inp):
                try:
                    exec(_part.strip(), {{}}, local_ns)
                except Exception:
                    pass
        # if exec produced no bindings it was a plain expression — eval it
        if not local_ns:
            _evaled = eval(inp)
            if isinstance(_evaled, tuple):
                # "arg1, arg2, ..." — each element is a separate function arg
                for _i, _v in enumerate(_evaled):
                    local_ns[f"_arg{{_i}}"] = _v
            else:
                local_ns["_arg"] = _evaled
        # call user function with args in insertion order
        if _solve_fn is not None:
            args = list(local_ns.values())
            actual = _solve_fn(*args) if args else _solve_fn()
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

print("{marker}" + json.dumps(results))
"""
    return harness


def run_code(code: str, test_cases: list, language: str = "python"):
    """Execute user code in a subprocess with strict timeout and resource caps."""
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

    # Per-run unpredictable marker — see module docstring.
    marker = f"__RESULTS_{uuid.uuid4().hex}__:"

    # Write to temp file
    harness = _build_test_harness(code, test_cases, marker)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, dir="/tmp"
    ) as f:
        f.write(harness)
        tmp_path = f.name

    start = time.monotonic()
    try:
        proc = subprocess.Popen(
            [sys.executable, tmp_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=_limit_resources if os.name == "posix" else None,
            env={
                "PATH": "/usr/local/bin:/usr/bin:/bin",
                "HOME": "/tmp",
                "PYTHONDONTWRITEBYTECODE": "1",
            },
        )
        try:
            raw_stdout, raw_stderr = proc.communicate(timeout=MAX_EXEC_SECS)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()  # drain buffers so the process is fully reaped
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
        elapsed_ms = int((time.monotonic() - start) * 1000)
        stdout = raw_stdout[:MAX_OUTPUT_BYTES]
        stderr = raw_stderr[:MAX_OUTPUT_BYTES]

        # Parse the structured results line. Only the harness's own,
        # per-run-random marker is recognized — anything the submission
        # itself printed cannot match it (see module docstring).
        test_results = []
        clean_stdout_lines = []
        for line in stdout.splitlines():
            if line.startswith(marker):
                try:
                    test_results = json.loads(line[len(marker):])
                except Exception:
                    pass
            else:
                clean_stdout_lines.append(line)
        clean_stdout = "\n".join(clean_stdout_lines)

        # Fail closed: no genuine, correctly-marked results line means the
        # run did not complete grading (e.g. a hard os._exit() escape) —
        # never treat that as a pass.
        is_correct = bool(test_results) and all(r.get("passed") for r in test_results)

        # Classify error
        error_type = None
        error_message = None
        if proc.returncode != 0 or stderr:
            error_message = stderr.strip()
            if "MemoryError" in stderr or proc.returncode in (-9, 137) and not test_results:
                error_type = "MemoryError"
            elif "SyntaxError" in stderr:
                error_type = "SyntaxError"
            elif "NameError" in stderr:
                error_type = "NameError"
            elif "TypeError" in stderr:
                error_type = "TypeError"
            elif "IndexError" in stderr or "KeyError" in stderr:
                error_type = "IndexError/KeyError"
            elif "RecursionError" in stderr:
                error_type = "RecursionError"
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
    return jsonify(result), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
