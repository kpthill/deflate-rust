#!/usr/bin/env python3
"""
test_deflate.py — run a DEFLATE compressor against the reference examples.

Usage:
    python3 test_deflate.py <executable> [--file <name>] [--strict]

The executable is invoked with the input file piped to stdin.  It must write
raw DEFLATE (RFC 1951) bytes to stdout and exit 0 on success.

Default mode (round-trip):
    Decompresses the output with Python's zlib and checks it matches the
    original input.  This is the correct test for a compressor — DEFLATE
    does not mandate a unique compressed form, so any valid encoding of the
    same bytes is a correct answer.

Strict mode (--strict):
    Also requires the compressed output to be bit-for-bit identical to the
    reference .deflate files (which were produced by zlib at level 6).
    Useful only if you are deliberately trying to replicate zlib's exact
    choices (block type, Huffman tree construction, LZ77 match selection).
    Your implementation will almost certainly not pass this without
    specifically targeting zlib compatibility.

Each run creates a timestamped directory under runs/ containing the compressed
output and stderr (if any) for every tested example, plus a summary.txt.
"""

import argparse
import os
import subprocess
import sys
import zlib
from datetime import datetime
from pathlib import Path


REPO_ROOT    = Path(__file__).resolve().parent
EXAMPLES_DIR = REPO_ROOT / "examples"
RUNS_DIR     = REPO_ROOT / "runs"


def find_examples() -> list[tuple[Path, Path]]:
    pairs = []
    for p in sorted(EXAMPLES_DIR.iterdir()):
        if p.name.startswith(".") or p.suffix == ".deflate":
            continue
        expected = EXAMPLES_DIR / (p.name + ".deflate")
        if expected.exists():
            pairs.append((p, expected))
    return pairs


def run_one(executable: str, input_path: Path, expected_path: Path,
            run_dir: Path, strict: bool) -> dict:
    name       = input_path.name
    input_data = input_path.read_bytes()
    expected   = expected_path.read_bytes()

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

    # Round-trip check: decompress with trusted zlib and compare to original.
    try:
        roundtripped = zlib.decompress(actual, wbits=-15)
    except zlib.error as exc:
        return {
            "status":        "invalid",
            "name":          name,
            "input_size":    len(input_data),
            "expected_size": len(expected),
            "actual_size":   len(actual),
            "returncode":    0,
            "decomp_error":  str(exc),
        }

    if roundtripped != input_data:
        return {
            "status":        "roundtrip_mismatch",
            "name":          name,
            "input_size":    len(input_data),
            "expected_size": len(expected),
            "actual_size":   len(actual),
            "returncode":    0,
            "got_size":      len(roundtripped),
        }

    # In strict mode, also require bit-for-bit match with the reference file.
    if strict:
        bit_match  = actual == expected
        size_match = len(actual) == len(expected)
        status = "pass" if bit_match else ("size_mismatch" if not size_match else "bit_mismatch")
    else:
        status = "pass"

    return {
        "status":        status,
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


def format_result(r: dict, strict: bool) -> str:
    name   = r["name"]
    in_sz  = r["input_size"]
    exp_sz = r["expected_size"]
    act_sz = r["actual_size"]

    match r["status"]:
        case "pass":
            ratio = act_sz / max(in_sz, 1) * 100
            detail = "bit-for-bit match" if strict else "round-trip ok"
            return (f"  PASS  {name:<42} "
                    f"{in_sz:>6} B → {act_sz:>6} B ({ratio:5.1f}%)  {detail}")
        case "error":
            rc  = r["returncode"]
            tag = f"exit={rc}" if rc is not None else "killed"
            return f" ERROR  {name:<42} {tag}  — {r['first_error']}"
        case "invalid":
            return (f"  FAIL  {name:<42} "
                    f"output is not valid DEFLATE: {r['decomp_error']}")
        case "roundtrip_mismatch":
            return (f"  FAIL  {name:<42} "
                    f"decompressed to {r['got_size']} B, expected {in_sz} B")
        case "size_mismatch":
            return (f"  FAIL  {name:<42} "
                    f"[strict] size: expected {exp_sz} B, got {act_sz} B")
        case "bit_mismatch":
            return (f"  FAIL  {name:<42} "
                    f"[strict] both {act_sz} B but content differs from reference")
        case _:
            return f"  ???   {name}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test a DEFLATE compressor against the reference examples.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Default: round-trip test (compress → decompress → compare to original).\n"
            "Any valid DEFLATE encoding of the input bytes is accepted.\n\n"
            "--strict: also require bit-for-bit match with the zlib level-6\n"
            "reference files.  Almost no implementation will pass this."
        ),
    )
    parser.add_argument("executable", help="path to the DEFLATE compressor binary")
    parser.add_argument(
        "--file", metavar="NAME",
        help="test only this example (basename, e.g. hello.txt)",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="require bit-for-bit match with reference .deflate files",
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

    mode   = "strict (round-trip + bit-for-bit)" if args.strict else "round-trip"
    header = (
        f"Run:        {run_dir}\n"
        f"Executable: {executable}\n"
        f"Mode:       {mode}\n"
        f"Examples:   {len(examples)}\n"
    )
    print(header)

    results = []
    for inp, exp in examples:
        r = run_one(executable, inp, exp, run_dir, strict=args.strict)
        results.append(r)
        print(format_result(r, strict=args.strict))

    n_pass = sum(1 for r in results if r["status"] == "pass")
    n_fail = sum(1 for r in results if r["status"] != "pass" and r["status"] != "error")
    n_err  = sum(1 for r in results if r["status"] == "error")
    footer = (
        f"\nResults: {n_pass} passed, {n_fail} failed, {n_err} errors"
        f"  ({len(results)} total)\n"
        f"Outputs saved to: {run_dir}"
    )
    print(footer)

    summary = header + "\n".join(format_result(r, args.strict) for r in results) + "\n" + footer + "\n"
    (run_dir / "summary.txt").write_text(summary)

    if n_fail > 0 or n_err > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
