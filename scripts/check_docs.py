#!/usr/bin/env python3
"""
Vérification minimale de la documentation : README présent,
docstrings sur modules/classes publiques. Utilisé par le workflow GitHub Actions.
"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def check_readme() -> bool:
    """Vérifie que README.md existe et n'est pas vide."""
    readme = ROOT / "README.md"
    if not readme.exists():
        print("❌ README.md manquant.")
        return False
    if readme.stat().st_size == 0:
        print("❌ README.md vide.")
        return False
    print("✔ README.md présent et non vide.")
    return True


def check_module_docstring(path: Path) -> bool:
    """Vérifie qu'un fichier Python a une docstring (module ou première classe/fonction)."""
    try:
        src = path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"❌ Impossible de lire {path}: {e}")
        return False
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        print(f"❌ Syntaxe invalide dans {path}: {e}")
        return False
    has_doc = ast.get_docstring(tree) is not None
    if not has_doc and tree.body:
        first = tree.body[0]
        if isinstance(first, (ast.ClassDef, ast.FunctionDef)):
            has_doc = ast.get_docstring(first) is not None
    if not has_doc:
        print(f"❌ Pas de docstring dans {path.relative_to(ROOT)}")
        return False
    return True


def check_docs() -> bool:
    """Vérifie README et docstrings des modules principaux."""
    ok = check_readme()
    for part in ["core", "agents"]:
        dir_path = ROOT / part
        if not dir_path.is_dir():
            continue
        for path in sorted(dir_path.glob("*.py")):
            if path.name == "__init__.py":
                continue
            ok = check_module_docstring(path) and ok
    if ok:
        print("✔ Vérification documentation OK.")
    return ok


if __name__ == "__main__":
    sys.exit(0 if check_docs() else 1)
