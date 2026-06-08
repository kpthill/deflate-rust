#!/usr/bin/env python3
"""
test_deflate.py — run a DEFLATE compressor against the reference examples.

Usage:
    python3 test_deflate.py <executable> [--file <name>]

The executable is invoked with the input file piped to stdin.  It must write
raw DEFLATE (RFC 1951) bytes to stdout and exit 0 on success.

Each run creates a timestamped directory under runs/ containing the compressed
output and stderr (if any) for every tested example, plus a summary.txt.
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


REPO_ROOT   = Path(__file__).resolve().parent
EXAMPLES_DIR = REPO_ROOT / "examples"
RUNS_DIR    = REPO_ROOT / "runs"


def find_examples() -> list[tuple[Path, Path]]:
    pairs = []
    for p in sorted(EXAMPLES_DIR.iterdir()):
        if p.name.startswith(".") or p.suffix == ".deflate":
            continue
        expected = EXAMPLES_DIR / (p.name + ".deflate")
        if expected.exists():
            pairs.append((p, expected))
    return pairs


def run_one(executable: str, input_path: Path, expected_path: Path, run_dir: Path) -> dict:
    name = input_path.name
    input_data  = input_path.read_bytes()
    expected    = expected_path.read_bytes()

    try:
        proc = subprocess.run(
            [executable],
            input=input_data,
            capture_output=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return _err(name, input_data, expected, returncode=None,
                    first_error="timed out after 30s", actual=b"")
    except OSError as exc:
        return _err(name, input_data, expected, returncode=None,
                    first_error=str(exc), actual=b"")

    actual       = proc.stdout
    stderr_bytes = proc.stderr

    (run_dir / (name + ".deflate")).write_bytes(actual)
    if stderr_bytes:
        (run_dir / (name + ".stderr")).write_bytes(stderr_bytes)

    if proc.returncode != 0:
        stderr_text = stderr_bytes.decode(errors="replace")
        first_err   = (stderr_text.splitlines() or ["(no stderr)"])[0]
        return _err(name, input_data, expected,
                    returncode=proc.returncode, first_error=first_err, actual=actual)

    bit_match  = actual == expected
    size_match = len(actual) == len(expected)

    return {
        "status":        "pass" if bit_match else ("size_mismatch" if not size_match else "bit_mismatch"),
        "name":          name,
        "input_size":    len(input_data),
        "expected_size": len(expected),
        "actual_size":   len(actual),
        "returncode":    0,
    }


def _err(name, input_data, expected, *, returncode, first_error, actual) -> dict:
    return {
        "status":        "error",
        "name":          name,
        "input_size":    len(input_data),
        "expected_size": len(expected),
        "actual_size":   len(actual),
        "returncode":    returncode,
        "first_error":   first_error,
    }


def format_result(r: dict) -> str:
    name   = r["name"]
    in_sz  = r["input_size"]
    exp_sz = r["expected_size"]
    act_sz = r["actual_size"]

    match r["status"]:
        case "pass":
            ratio = act_sz / max(in_sz, 1) * 100
            return (f"  PASS  {name:<42} "
                    f"{in_sz:>6} B → {act_sz:>6} B ({ratio:5.1f}%)  bit-for-bit match")
        case "error":
            rc  = r["returncode"]
            tag = f"exit={rc}" if rc is not None else "killed"
            return f" ERROR  {name:<42} {tag}  — {r['first_error']}"
        case "size_mismatch":
            return (f"  FAIL  {name:<42} "
                    f"size: expected {exp_sz} B, got {act_sz} B")
        case "bit_mismatch":
            return (f"  FAIL  {name:<42} "
                    f"both {act_sz} B but content differs from reference")
        case _:
            return f"  ???   {name}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test a DEFLATE compressor against the reference examples.",
        epilog=(
            "The executable is called with the input file on stdin.\n"
            "It must write raw DEFLATE (RFC 1951) bytes to stdout and exit 0."
        ),
    )
    parser.add_argument("executable", help="path to the DEFLATE compressor binary")
    parser.add_argument(
        "--file", metavar="NAME",
        help="test only this example (basename, e.g. hello.txt)",
    )
    args = parser.parse_args()

    executable = os.path.abspath(args.executable)
    if not os.path.isfile(executable):
        sys.exit(f"error: not found: {executable}")
    if not os.access(executable, os.X_OK):
        sys.exit(f"error: not executable: {executable}")

    all_examples = find_examples()
    if not all_examples:
        sys.exit(f"error: no paired examples found in {EXAMPLES_DIR}")

    if args.file:
        examples = [(inp, exp) for inp, exp in all_examples if inp.name == args.file]
        if not examples:
            available = "  ".join(inp.name for inp, _ in all_examples)
            sys.exit(f"error: '{args.file}' not found.\nAvailable: {available}")
    else:
        examples = all_examples

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    run_dir   = RUNS_DIR / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)

    header = (
        f"Run:        {run_dir}\n"
        f"Executable: {executable}\n"
        f"Examples:   {len(examples)}\n"
    )
    print(header)

    results = []
    for inp, exp in examples:
        r = run_one(executable, inp, exp, run_dir)
        results.append(r)
        print(format_result(r))

    n_pass = sum(1 for r in results if r["status"] == "pass")
    n_fail = sum(1 for r in results if r["status"] in ("size_mismatch", "bit_mismatch"))
    n_err  = sum(1 for r in results if r["status"] == "error")
    footer = (
        f"\nResults: {n_pass} passed, {n_fail} failed, {n_err} errors"
        f"  ({len(results)} total)\n"
        f"Outputs saved to: {run_dir}"
    )
    print(footer)

    summary = header + "\n".join(format_result(r) for r in results) + "\n" + footer + "\n"
    (run_dir / "summary.txt").write_text(summary)

    if n_fail > 0 or n_err > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
