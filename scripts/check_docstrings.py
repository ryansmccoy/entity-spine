#!/usr/bin/env python3
"""
Check docstring coverage across entityspine source code.

Usage:
    python scripts/check_docstrings.py
"""

import ast
from pathlib import Path


def check_docstrings(src_path: str):
    """Analyze docstring coverage in Python files."""
    results = {
        "classes": 0,
        "classes_with_docs": 0,
        "functions": 0,
        "funcs_with_docs": 0,
        "modules": 0,
        "mods_with_docs": 0,
    }
    missing = []

    for py_file in Path(src_path).rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())

            rel_path = py_file.relative_to(src_path)

            # Check module docstring
            results["modules"] += 1
            if ast.get_docstring(tree):
                results["mods_with_docs"] += 1
            else:
                missing.append(f"{rel_path} (module)")

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    results["classes"] += 1
                    if ast.get_docstring(node):
                        results["classes_with_docs"] += 1
                    else:
                        missing.append(f"{rel_path}:{node.lineno} class {node.name}")
                elif isinstance(node, ast.FunctionDef):
                    # Skip private methods (but include dunder methods)
                    if node.name.startswith("_") and not node.name.startswith("__"):
                        continue
                    results["functions"] += 1
                    if ast.get_docstring(node):
                        results["funcs_with_docs"] += 1
                    else:
                        missing.append(f"{rel_path}:{node.lineno} def {node.name}")
        except Exception as e:
            print(f"Error parsing {py_file}: {e}")

    return results, missing


def main():
    """Run docstring analysis."""
    src_path = Path(__file__).parent.parent / "src" / "entityspine"
    results, missing = check_docstrings(str(src_path))

    print("=" * 50)
    print("DOCSTRING COVERAGE REPORT")
    print("=" * 50)
    
    mod_pct = 100 * results["mods_with_docs"] // max(results["modules"], 1)
    cls_pct = 100 * results["classes_with_docs"] // max(results["classes"], 1)
    fn_pct = 100 * results["funcs_with_docs"] // max(results["functions"], 1)
    
    print(f"Modules:   {results['mods_with_docs']:3d}/{results['modules']:3d} ({mod_pct}%)")
    print(f"Classes:   {results['classes_with_docs']:3d}/{results['classes']:3d} ({cls_pct}%)")
    print(f"Functions: {results['funcs_with_docs']:3d}/{results['functions']:3d} ({fn_pct}%)")
    print()
    
    overall = (
        results["mods_with_docs"]
        + results["classes_with_docs"]
        + results["funcs_with_docs"]
    )
    total = results["modules"] + results["classes"] + results["functions"]
    overall_pct = 100 * overall // max(total, 1)
    print(f"OVERALL:   {overall:3d}/{total:3d} ({overall_pct}%)")
    print()

    if missing:
        print("=" * 50)
        print(f"MISSING DOCSTRINGS ({len(missing)} items)")
        print("=" * 50)
        for m in missing[:30]:
            print(f"  - {m}")
        if len(missing) > 30:
            print(f"  ... and {len(missing) - 30} more")


if __name__ == "__main__":
    main()
