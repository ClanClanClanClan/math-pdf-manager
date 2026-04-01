#!/usr/bin/env python3
"""
Ultra Module Splitter - Splits large Python modules into smaller, focused components
"""

import ast
import os
import textwrap
from pathlib import Path
from typing import Dict, List, Tuple


class ModuleSplitter:
    """Splits large Python modules into smaller, focused components."""

    def __init__(self, max_lines: int = 500):
        self.max_lines = max_lines

    def analyze_module(self, file_path: Path) -> Dict:
        """Analyze a module to determine how to split it."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.split("\n")

        tree = ast.parse(content)

        # Categorize components
        components = {
            "imports": [],
            "constants": [],
            "exceptions": [],
            "utils": [],
            "models": [],
            "handlers": [],
            "validators": [],
            "main_class": None,
            "functions": [],
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if "Exception" in node.name or "Error" in node.name:
                    components["exceptions"].append(node)
                elif "Model" in node.name or "Schema" in node.name:
                    components["models"].append(node)
                elif "Handler" in node.name or "Manager" in node.name:
                    components["handlers"].append(node)
                elif "Validator" in node.name:
                    components["validators"].append(node)
                elif not components["main_class"]:
                    components["main_class"] = node

            elif isinstance(node, ast.FunctionDef):
                if node.name.startswith("_"):
                    components["utils"].append(node)
                else:
                    components["functions"].append(node)

        return {
            "file_path": file_path,
            "total_lines": len(lines),
            "components": components,
            "needs_split": len(lines) > self.max_lines,
        }

    def create_split_plan(self, analysis: Dict) -> List[Dict]:
        """Create a plan for splitting the module."""
        if not analysis["needs_split"]:
            return []

        base_name = analysis["file_path"].stem
        base_dir = analysis["file_path"].parent

        split_plan = []

        # Create separate files for each component type
        if analysis["components"]["exceptions"]:
            split_plan.append(
                {
                    "new_file": base_dir / f"{base_name}_exceptions.py",
                    "components": analysis["components"]["exceptions"],
                    "type": "exceptions",
                }
            )

        if analysis["components"]["models"]:
            split_plan.append(
                {
                    "new_file": base_dir / f"{base_name}_models.py",
                    "components": analysis["components"]["models"],
                    "type": "models",
                }
            )

        if analysis["components"]["validators"]:
            split_plan.append(
                {
                    "new_file": base_dir / f"{base_name}_validators.py",
                    "components": analysis["components"]["validators"],
                    "type": "validators",
                }
            )

        if analysis["components"]["utils"]:
            split_plan.append(
                {
                    "new_file": base_dir / f"{base_name}_utils.py",
                    "components": analysis["components"]["utils"],
                    "type": "utils",
                }
            )

        return split_plan


def main():
    """Main function to split large modules in src directory."""
    splitter = ModuleSplitter(max_lines=500)

    # Find large modules
    src_dir = Path("src")
    large_modules = []

    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" not in str(py_file):
            with open(py_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) > 500:
                large_modules.append((py_file, len(lines)))

    # Sort by size
    large_modules.sort(key=lambda x: x[1], reverse=True)

    print(f"Found {len(large_modules)} large modules to split:")
    for module, lines in large_modules[:10]:
        print(f"  {module.relative_to('.')}: {lines} lines")

    # Analyze each module
    print("\nAnalyzing modules for splitting...")
    for module, _ in large_modules[:5]:
        analysis = splitter.analyze_module(module)
        if analysis["needs_split"]:
            plan = splitter.create_split_plan(analysis)
            if plan:
                print(f"\n{module.name} can be split into:")
                for item in plan:
                    print(f"  - {item['new_file'].name} ({item['type']})")


if __name__ == "__main__":
    main()
