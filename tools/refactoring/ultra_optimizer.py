#!/usr/bin/env python3
"""
Ultra Code Optimizer - Round 3
Splits large files, removes dead code, optimizes imports
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple

import black
import isort


class UltraOptimizer:
    """Ultimate code optimization tool."""

    def __init__(self):
        self.stats = {
            "files_processed": 0,
            "lines_removed": 0,
            "imports_optimized": 0,
            "functions_extracted": 0,
            "classes_split": 0,
        }

    def optimize_file(self, file_path: Path) -> bool:
        """Optimize a single Python file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                original_content = f.read()
                original_lines = len(original_content.splitlines())

            # Parse AST
            tree = ast.parse(original_content)

            # Remove unused imports
            tree = self.remove_unused_imports(tree, original_content)

            # Remove dead code
            tree = self.remove_dead_code(tree)

            # Convert back to code
            optimized_content = ast.unparse(tree)

            # Format with black and isort
            optimized_content = isort.code(optimized_content)
            optimized_content = black.format_str(optimized_content, mode=black.Mode())

            # Calculate savings
            optimized_lines = len(optimized_content.splitlines())
            lines_saved = original_lines - optimized_lines

            if lines_saved > 0:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(optimized_content)
                self.stats["lines_removed"] += lines_saved
                return True

        except Exception as e:
            print(f"Error optimizing {file_path}: {e}")
        return False

    def remove_unused_imports(self, tree: ast.AST, content: str) -> ast.AST:
        """Remove unused imports from AST."""
        # Collect all names used in the file
        used_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name):
                    used_names.add(node.value.id)

        # Filter imports
        new_body = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                new_names = []
                for alias in node.names:
                    name = alias.asname or alias.name.split(".")[0]
                    if name in used_names or name in {"__annotations__", "TYPE_CHECKING"}:
                        new_names.append(alias)
                if new_names:
                    node.names = new_names
                    new_body.append(node)
                else:
                    self.stats["imports_optimized"] += 1
            elif isinstance(node, ast.ImportFrom):
                new_names = []
                for alias in node.names:
                    name = alias.asname or alias.name
                    if name in used_names or name == "*":
                        new_names.append(alias)
                if new_names:
                    node.names = new_names
                    new_body.append(node)
                else:
                    self.stats["imports_optimized"] += 1
            else:
                new_body.append(node)

        tree.body = new_body
        return tree

    def remove_dead_code(self, tree: ast.AST) -> ast.AST:
        """Remove dead code patterns."""

        class DeadCodeRemover(ast.NodeTransformer):
            def visit_If(self, node):
                # Remove if False blocks
                if isinstance(node.test, ast.Constant) and not node.test.value:
                    return None
                # Remove empty if blocks
                if not node.body and not node.orelse:
                    return None
                return self.generic_visit(node)

            def visit_FunctionDef(self, node):
                # Remove functions that only pass
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    if not node.name.startswith("_"):  # Keep private placeholders
                        return None
                return self.generic_visit(node)

        return DeadCodeRemover().visit(tree)

    def split_large_file(self, file_path: Path, max_lines: int = 500) -> List[Path]:
        """Split a large file into smaller modules."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.splitlines()

        if len(lines) <= max_lines:
            return []

        tree = ast.parse(content)

        # Group related components
        imports = []
        constants = []
        exceptions = []
        utils = []
        classes = []
        main_functions = []

        for node in tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(node)
            elif isinstance(node, ast.ClassDef):
                if "Exception" in node.name or "Error" in node.name:
                    exceptions.append(node)
                else:
                    classes.append(node)
            elif isinstance(node, ast.FunctionDef):
                if node.name.startswith("_"):
                    utils.append(node)
                else:
                    main_functions.append(node)
            elif isinstance(node, ast.Assign):
                constants.append(node)

        # Create split files
        base_name = file_path.stem
        base_dir = file_path.parent
        created_files = []

        if exceptions:
            exc_file = base_dir / f"{base_name}_exceptions.py"
            self._write_module(exc_file, imports, exceptions)
            created_files.append(exc_file)
            self.stats["classes_split"] += len(exceptions)

        if utils:
            utils_file = base_dir / f"{base_name}_utils.py"
            self._write_module(utils_file, imports, utils)
            created_files.append(utils_file)
            self.stats["functions_extracted"] += len(utils)

        return created_files

    def _write_module(self, file_path: Path, imports: List, nodes: List):
        """Write a module with imports and nodes."""
        module = ast.Module(body=imports + nodes, type_ignores=[])
        code = ast.unparse(module)
        code = isort.code(code)
        code = black.format_str(code, mode=black.Mode())

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)

    def optimize_directory(self, directory: Path):
        """Optimize all Python files in directory."""
        py_files = list(directory.rglob("*.py"))

        print(f"Optimizing {len(py_files)} Python files...")

        for py_file in py_files:
            if "__pycache__" not in str(py_file):
                self.stats["files_processed"] += 1

                # Check file size
                with open(py_file, "r", encoding="utf-8") as f:
                    lines = len(f.readlines())

                if lines > 500:
                    print(f"Splitting large file: {py_file} ({lines} lines)")
                    self.split_large_file(py_file)

                # Optimize the file
                if self.optimize_file(py_file):
                    print(f"Optimized: {py_file}")

        # Print statistics
        print("\n=== OPTIMIZATION COMPLETE ===")
        print(f"Files processed: {self.stats['files_processed']}")
        print(f"Lines removed: {self.stats['lines_removed']}")
        print(f"Imports optimized: {self.stats['imports_optimized']}")
        print(f"Functions extracted: {self.stats['functions_extracted']}")
        print(f"Classes split: {self.stats['classes_split']}")


if __name__ == "__main__":
    optimizer = UltraOptimizer()
    optimizer.optimize_directory(Path("src"))
