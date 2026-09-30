"""Sandboxed execution helpers for the benchmark engine.

User code is executed in a **separate Python subprocess** with:

* an isolated interpreter session (``python -I``),
* a hard wall-clock timeout,
* POSIX resource limits (address space + CPU seconds),
* a minimal generated driver script that imports the user module from a
  temporary file, generates deterministic inputs, and reports timings and
  peak memory as a single JSON line.

This is a first-level sandbox suitable for an academic deployment; a
production deployment would additionally use OS containers (see
``docs/architecture.md`` → Security notes).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

RESULT_MARKER = "@@BENCH@@"

# --------------------------------------------------------------------------- #
# Driver templates
# --------------------------------------------------------------------------- #
_DRIVER_TEMPLATE = '''\
"""Generated benchmark driver — executes one user algorithm."""
import json, random, sys, time, tracemalloc
import importlib.util

sys.setrecursionlimit(50000)  # accommodate deep linear recursion (e.g. memoised fib)

CODE_PATH = {code_path!r}
FN_NAME = {fn_name!r}
SIZES = {sizes!r}
REPEATS = {repeats!r}
INPUT_SPEC = {input_spec!r}
TIME_BUDGET = {time_budget!r}


def load_function():
    spec = importlib.util.spec_from_file_location("user_algorithm", CODE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, FN_NAME)


def make_graph(rng, n):
    nodes = list(range(n))
    return {{v: rng.sample([u for u in nodes if u != v], min(5, max(n - 1, 0)))
            for v in nodes}}


def make_args(rng, n):
    args = []
    for kind in INPUT_SPEC:
        if kind == "int_list":
            args.append([rng.randint(-1000, 1000) for _ in range(n)])
        elif kind == "int_list_sorted":
            args.append(sorted(rng.sample(range(-10 ** 6, 10 ** 6), n)))
        elif kind == "int":
            args.append(n)
        elif kind == "int_start":
            args.append(0)
        elif kind == "graph":
            args.append(make_graph(rng, n))
        elif kind == "string":
            args.append("".join(rng.choice("abcde") for _ in range(n)))
        else:
            args.append(None)
    # A search target is drawn from the generated collection.
    for i, kind in enumerate(INPUT_SPEC):
        if kind == "int_target":
            pool = next((a for a in args if isinstance(a, list)), None)
            args[i] = rng.choice(pool) if pool else 0
    return args


def main():
    fn = load_function()
    rng = random.Random(42)
    points = []
    try:
        fn(*make_args(rng, min(SIZES) if SIZES else 8))  # warm-up (imports, caches)
    except Exception:
        pass
    for n in SIZES:
        try:
            best = float("inf")
            for _ in range(REPEATS):
                args = make_args(rng, n)
                t0 = time.perf_counter()
                fn(*args)
                best = min(best, time.perf_counter() - t0)
            args = make_args(rng, n)
            tracemalloc.start()
            fn(*args)
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            points.append({{"n": n, "time_ms": round(best * 1000.0, 4),
                            "memory_kb": round(peak / 1024.0, 2)}})
            if best > TIME_BUDGET:
                break
        except Exception as exc:  # noqa: BLE001 - reported back to the UI
            points.append({{"n": n, "error": f"{{type(exc).__name__}}: {{exc}}"}})
            break
    print("{marker}" + json.dumps({{"points": points, "fn": FN_NAME}}))


if __name__ == "__main__":
    main()
'''

_AGREEMENT_TEMPLATE = '''\
"""Generated agreement driver — checks whether two algorithms agree on outputs."""
import json, random, sys
import importlib.util

sys.setrecursionlimit(50000)


def load(path, name):
    spec = importlib.util.spec_from_file_location("u_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, name)


PATH_A = {path_a!r}
PATH_B = {path_b!r}
NAME_A = {name_a!r}
NAME_B = {name_b!r}
SPEC_A = {spec_a!r}
SPEC_B = {spec_b!r}
N = {n!r}
SEEDS = {seeds!r}


def make_graph(rng, n):
    nodes = list(range(n))
    return {{v: rng.sample([u for u in nodes if u != v], min(5, max(n - 1, 0)))
            for v in nodes}}


def build_args(spec, rng, n, base):
    args = []
    for kind in spec:
        if kind == "int_list":
            args.append(list(base))
        elif kind == "int_list_sorted":
            args.append(list(base))
        elif kind == "int":
            args.append(n)
        elif kind == "int_start":
            args.append(0)
        elif kind == "graph":
            args.append(make_graph(rng, n))
        elif kind == "int_target":
            args.append(rng.choice(base) if base else 0)
        else:
            args.append(None)
    return args


def main():
    fn_a, fn_b = load(PATH_A, NAME_A), load(PATH_B, NAME_B)
    match, mismatch, errored = 0, 0, 0
    for seed in SEEDS:
        rng = random.Random(seed)
        if "int_list_sorted" in SPEC_A or "int_list_sorted" in SPEC_B:
            base = sorted(rng.sample(range(-10 ** 6, 10 ** 6), N))
        else:
            base = [rng.randint(-1000, 1000) for _ in range(N)]
        try:
            # A fresh RNG per algorithm (same seed) guarantees identical args.
            ra = fn_a(*build_args(SPEC_A, random.Random(seed), N, base))
            rb = fn_b(*build_args(SPEC_B, random.Random(seed), N, base))
            if ra == rb:
                match += 1
            else:
                mismatch += 1
        except Exception:
            errored += 1
    print("{marker}" + json.dumps({{"match": match, "mismatch": mismatch,
                                    "errored": errored, "samples": len(SEEDS)}}))


if __name__ == "__main__":
    main()
'''


def write_module(source: str, directory: str, stem: str) -> str:
    """Persist user code to a temporary module file and return its path."""
    path = os.path.join(directory, f"{stem}.py")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(source)
    return path


def _posix_limits(max_memory_mb: int, cpu_seconds: int):
    def _apply():  # pragma: no cover - executed inside the child process
        try:
            import resource

            mem = max_memory_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        except Exception:
            pass

    return _apply


def run_driver(script_path: str, timeout: int, max_memory_mb: int) -> dict:
    """Execute a driver script in a restricted subprocess and parse its JSON."""
    preexec = _posix_limits(max_memory_mb, timeout) if os.name == "posix" else None
    env = {k: v for k, v in os.environ.items() if k in {"PATH", "SYSTEMROOT", "LANG"}}
    proc = subprocess.run(
        [sys.executable, "-I", script_path],
        capture_output=True,
        text=True,
        timeout=timeout,
        preexec_fn=preexec,
        env=env,
        cwd=os.path.dirname(script_path),
    )
    for line in reversed((proc.stdout or "").splitlines()):
        if line.startswith(RESULT_MARKER):
            return json.loads(line[len(RESULT_MARKER):])
    stderr = (proc.stderr or "").strip().splitlines()
    raise RuntimeError(
        "benchmark driver produced no result: " + (stderr[-1] if stderr else "unknown error")
    )


def build_benchmark_driver(
    code_path: str, fn_name: str, sizes: list[int], repeats: int,
    input_spec: list[str], time_budget: float, out_path: str,
) -> str:
    """Render the timing/memory driver script to ``out_path``."""
    source = _DRIVER_TEMPLATE.format(
        code_path=code_path, fn_name=fn_name, sizes=sizes, repeats=repeats,
        input_spec=input_spec, time_budget=time_budget, marker=RESULT_MARKER,
    )
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(source)
    return out_path


def build_agreement_driver(
    path_a: str, path_b: str, name_a: str, name_b: str,
    spec_a: list[str], spec_b: list[str], n: int, seeds: list[int], out_path: str,
) -> str:
    """Render the output-agreement driver script to ``out_path``."""
    source = _AGREEMENT_TEMPLATE.format(
        path_a=path_a, path_b=path_b, name_a=name_a, name_b=name_b,
        spec_a=spec_a, spec_b=spec_b, n=n, seeds=seeds, marker=RESULT_MARKER,
    )
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(source)
    return out_path


def temp_directory() -> str:
    """Create a private temporary directory for one benchmark run."""
    return tempfile.mkdtemp(prefix="algobench-")
