"""Helper utilities for code modification."""

import re
from pathlib import Path
from typing import List, Optional, Set

FILE_TYPES_TO_INCLUDE = {
    ".css",
    ".html",
    ".json",
    ".js",
    ".jsx",
    ".md",
    ".py",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
}

DIRECTORIES_TO_EXCLUDE = {
    ".*",
    "build",
    "dist",
    "env",
    ".env",
    ".git",
    ".next",
    "node_modules",
    ".mypy",
    ".mypy_cache",
    "mypy_cache",
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "__pypackages__",
    ".ruff_cache",
}

FILES_TO_EXCLUDE = {
    ".DS_Store",
    "thumbs.db",
    "package-lock.json",
    "yarn.lock",
    "*/migrations/*",
}


class ImportEditor:
    """Robust editor for managing Python import statements."""

    @staticmethod
    def add_to_import(
        file_path: Path, module: str, items: List[str], force: bool = False
    ) -> bool:
        """
        Add items to an existing import statement or create a new one.

        Args:
            file_path: Path to the Python file
            module: Module name (e.g., 'django.urls')
            items: List of items to import (e.g., ['include', 'path'])
            force: If True, adds even if items might already exist

        Returns:
            True if changes were made, False otherwise
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = file_path.read_text()
        lines = content.split("\n")

        # Find all existing imports from the module
        existing_items = ImportEditor._find_existing_imports(lines, module)

        # Determine what needs to be added
        items_to_add = set(items) - existing_items if not force else set(items)

        if not items_to_add:
            return False  # Nothing to add

        # Try to find and update existing import line
        import_line_idx = ImportEditor._find_import_line(lines, module)

        if import_line_idx is not None:
            # Update existing import
            lines[import_line_idx] = ImportEditor._update_import_line(
                lines[import_line_idx], module, existing_items | items_to_add
            )
        else:
            # Add new import line
            insert_idx = ImportEditor._find_import_insert_position(lines)
            new_import = f"from {module} import {', '.join(sorted(items_to_add))}"
            lines.insert(insert_idx, new_import)

        # Write back
        file_path.write_text("\n".join(lines))
        return True

    @staticmethod
    def _find_existing_imports(lines: List[str], module: str) -> Set[str]:
        """Find all items already imported from a module."""
        items = set()

        # Pattern: from module import item1, item2, ...
        pattern = rf"from\s+{re.escape(module)}\s+import\s+(.+)"

        for line in lines:
            match = re.match(pattern, line.strip())
            if match:
                import_part = match.group(1)
                # Split by comma and clean up
                for item in import_part.split(","):
                    item = item.strip()
                    # Handle "as" aliases
                    if " as " in item:
                        item = item.split(" as ")[0].strip()
                    if item:
                        items.add(item)

        return items

    @staticmethod
    def _find_import_line(lines: List[str], module: str) -> Optional[int]:
        """Find the line index of an import from the specified module."""
        pattern = rf"from\s+{re.escape(module)}\s+import\s+"

        for idx, line in enumerate(lines):
            if re.match(pattern, line.strip()):
                return idx

        return None

    @staticmethod
    def _update_import_line(line: str, module: str, all_items: Set[str]) -> str:
        """Update an import line with new items."""
        sorted_items = ", ".join(sorted(all_items))
        return f"from {module} import {sorted_items}"

    @staticmethod
    def _find_import_insert_position(lines: List[str]) -> int:
        """Find the best position to insert a new import statement."""
        # Find the last import statement
        last_import_idx = -1

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                last_import_idx = idx

        # Insert after the last import, or at the beginning if no imports found
        if last_import_idx >= 0:
            return last_import_idx + 1

        # Find first non-comment, non-docstring line
        in_docstring = False
        for idx, line in enumerate(lines):
            stripped = line.strip()

            # Handle docstrings
            if '"""' in stripped or "'''" in stripped:
                in_docstring = not in_docstring
                continue

            if in_docstring or not stripped or stripped.startswith("#"):
                continue

            return idx

        return 0


class ListEditor:
    """Editor for managing Python list structures in code."""

    @staticmethod
    def add_to_list(
        file_path: Path,
        list_name: str,
        item: str,
        force: bool = False,
        indent: str = "    ",
    ) -> bool:
        """
        Add an item to a Python list in a file.

        Args:
            file_path: Path to the Python file
            list_name: Name of the list variable (e.g., 'urlpatterns', 'INSTALLED_APPS')
            item: Item to add (as a string, will be inserted as-is)
            force: If True, adds even if similar item exists
            indent: Indentation to use for the new item

        Returns:
            True if changes were made, False otherwise
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = file_path.read_text()
        lines = content.split("\n")

        # Check if item already exists
        if not force and item.strip() in content:
            return False

        # Find the list and its closing bracket
        list_start_idx = None
        list_end_idx = None

        for idx, line in enumerate(lines):
            if f"{list_name} = [" in line or f"{list_name}=[" in line:
                list_start_idx = idx
                # Find closing bracket
                bracket_count = 0
                for j in range(idx, len(lines)):
                    bracket_count += lines[j].count("[") - lines[j].count("]")
                    if bracket_count == 0:
                        list_end_idx = j
                        break
                break

        if list_start_idx is None or list_end_idx is None:
            raise ValueError(f"Could not find {list_name} in {file_path}")

        # Insert the item before the closing bracket
        lines.insert(list_end_idx, f"{indent}{item}")

        # Write back
        file_path.write_text("\n".join(lines))
        return True
