def main() -> int:
    ci_dir = Path(__file__).resolve().parent
    python = sys.executable

    checks_dir = ci_dir / "checks"

    required = [
    "determinism_checks.py",
    "semantic_immutability_check.py",
    "ordering_contract_check.py",   # ✅ 新增
    "safety_checks.py",
    "explainability_checks.py",
    ]

    for name in required:
        path = checks_dir / name
        if not path.exists():
            fail(f"Missing required CI check: {name}")

    # ✅ deterministic execution order（重要，infra test會檢）
    _run(python, checks_dir / "determinism_checks.py", "determinism")
    _run(python, checks_dir / "semantic_immutability_check.py", "immutability")
    _run(python, checks_dir / "safety_checks.py", "safety")
    _run(python, checks_dir / "explainability_checks.py", "explainability")
    _run(python, checks_dir / "ordering_contract_check.py", "ordering")


    return 0
