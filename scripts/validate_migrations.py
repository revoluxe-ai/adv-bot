#!/usr/bin/env python3
"""
Migration Chain Validation Script

This script validates the integrity of Alembic migration files to ensure:
1. All migrations have valid revision IDs
2. All referenced parent revisions exist
3. There's exactly one head revision (or properly merged heads)
4. No circular dependencies exist
"""

import os
import re
import sys
from pathlib import Path


def analyze_migration(filepath: Path) -> dict:
    """Extract migration metadata from a file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract revision
    rev_match = re.search(r'revision:\s*(?:str\s*=\s*)?["\']([^"\']+)["\']', content)
    if not rev_match:
        return None
    revision = rev_match.group(1)
    
    # Extract down_revision
    # This handles multiple typing patterns: str | None, Union[str, None], etc.
    # We use [^=] to avoid matching across multiple assignments
    down_match = re.search(
        r'down_revision[:\s]*(?:[^=]*?)\s*=\s*(.+)',
        content,
        re.MULTILINE
    )
    if not down_match:
        return None
    
    down_rev_str = down_match.group(1)
    
    # Parse the down revision
    if 'None' in down_rev_str and '(' not in down_rev_str:
        down_revision = None
    elif '(' in down_rev_str:
        # Tuple of revisions (merge migration)
        revs = re.findall(r'["\']([^"\']+)["\']', down_rev_str)
        down_revision = tuple(revs) if revs else None
    else:
        # Single revision
        rev_match = re.search(r'["\']([^"\']+)["\']', down_rev_str)
        if rev_match:
            down_revision = rev_match.group(1)
        else:
            down_revision = None
    
    return {
        'revision': revision,
        'down_revision': down_revision,
        'filename': filepath.name,
    }


def validate_migrations(versions_dir: Path) -> tuple[bool, list[str]]:
    """
    Validate all migrations in the versions directory.
    
    Returns:
        tuple[bool, list[str]]: (is_valid, error_messages)
            - is_valid: True if all validations pass, False otherwise
            - error_messages: List of error descriptions (empty if valid)
    """
    errors = []
    migrations = {}
    
    # Parse all migration files
    for filepath in sorted(versions_dir.glob('*.py')):
        if filepath.name == '__init__.py':
            continue
        
        info = analyze_migration(filepath)
        if not info:
            errors.append(f"❌ Could not parse {filepath.name}")
            continue
        
        rev = info['revision']
        if rev in migrations:
            errors.append(
                f"❌ Duplicate revision {rev}: {info['filename']} and "
                f"{migrations[rev]['filename']}"
            )
        
        migrations[rev] = info
    
    if not migrations:
        errors.append("❌ No migration files found")
        return False, errors
    
    print(f"✓ Found {len(migrations)} migration files")
    
    # Check for missing parent revisions
    all_revisions = set(migrations.keys())
    parent_revisions = set()
    
    for rev, info in migrations.items():
        down = info['down_revision']
        if down is None:
            continue
        elif isinstance(down, tuple):
            parent_revisions.update(down)
            for parent in down:
                if parent not in all_revisions:
                    errors.append(
                        f"❌ {info['filename']} references missing parent: {parent}"
                    )
        else:
            parent_revisions.add(down)
            if down not in all_revisions:
                errors.append(
                    f"❌ {info['filename']} references missing parent: {down}"
                )
    
    if not errors:
        print("✓ All parent revisions exist")
    
    # Find heads (revisions with no children)
    heads = all_revisions - parent_revisions
    
    if len(heads) == 0:
        errors.append("❌ No head revision found (circular dependency?)")
    elif len(heads) == 1:
        head = list(heads)[0]
        print(f"✓ Single head revision: {head}")
    else:
        heads_list = sorted(heads)
        if len(heads_list) == 2:
            merge_cmd = f"alembic merge -m \"merge message\" {' '.join(heads_list)}"
        else:
            merge_cmd = f"alembic merge -m \"merge message\" {' '.join(heads_list[:2])} (and {len(heads_list) - 2} more)"
        
        errors.append(
            f"❌ Multiple heads found: {', '.join(heads)}. "
            f"Merge them with: {merge_cmd}"
        )
    
    # Find roots (revisions with no parents)
    roots = [rev for rev, info in migrations.items() if info['down_revision'] is None]
    
    if len(roots) == 0:
        errors.append("❌ No root revision found (circular dependency?)")
    else:
        print(f"✓ Found {len(roots)} root revision(s): {', '.join(roots)}")
    
    return len(errors) == 0, errors


def main() -> int:
    """Main entry point."""
    project_root = Path(__file__).parent.parent
    
    # Try common locations for alembic versions directory
    possible_paths = [
        project_root / "alembic" / "versions",
        project_root / "migrations" / "versions",
        project_root / "db" / "alembic" / "versions",
    ]
    
    versions_dir = None
    for path in possible_paths:
        if path.exists():
            versions_dir = path
            break
    
    if not versions_dir:
        print(f"❌ Versions directory not found. Tried:")
        for path in possible_paths:
            print(f"   - {path}")
        return 1
    
    print("=" * 70)
    print("Alembic Migration Chain Validation")
    print("=" * 70)
    print()
    
    valid, errors = validate_migrations(versions_dir)
    
    if errors:
        print("\nErrors found:")
        for error in errors:
            print(f"  {error}")
    
    print("\n" + "=" * 70)
    if valid:
        print("✅ Migration chain is valid!")
        return 0
    else:
        print(f"❌ Validation failed with {len(errors)} error(s)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
