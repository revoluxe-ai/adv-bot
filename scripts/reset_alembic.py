#!/usr/bin/env python3
"""
Alembic Migration Reset Helper Script

This script helps fix the "Can't locate revision identified by '6941eea4ae8b'" error
by stamping the database to the current head revision.

Usage:
    python scripts/reset_alembic.py --check         # Check current database revision
    python scripts/reset_alembic.py --stamp         # Stamp database to current head
    python scripts/reset_alembic.py --force-stamp   # Force stamp even if validation fails
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], capture: bool = True) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    # Try to run with poetry if available, otherwise run directly
    project_root = Path(__file__).parent.parent
    
    # Check if poetry is available and this is a poetry project
    poetry_lock = project_root / "poetry.lock"
    if poetry_lock.exists():
        # Prepend 'poetry run' to the command
        cmd = ["poetry", "run"] + cmd
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            cwd=project_root,
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def get_current_revision() -> str | None:
    """Get the current database revision."""
    returncode, stdout, stderr = run_command(["alembic", "current"])
    if returncode != 0:
        print(f"Error getting current revision: {stderr}")
        return None
    
    # Parse output like "6eb95f5a8c66 (head)"
    if stdout.strip():
        parts = stdout.strip().split()
        if parts:
            return parts[0]
    return None


def get_head_revision() -> str | None:
    """Get the head revision from the codebase."""
    returncode, stdout, stderr = run_command(["alembic", "heads"])
    if returncode != 0:
        print(f"Error getting head revision: {stderr}")
        return None
    
    # Parse output like "6eb95f5a8c66 (head)"
    if stdout.strip():
        parts = stdout.strip().split()
        if parts:
            return parts[0]
    return None


def check_revision() -> None:
    """Check the current database revision status."""
    print("Checking database revision status...")
    print("-" * 60)
    
    current = get_current_revision()
    head = get_head_revision()
    
    print(f"Current database revision: {current or 'Unknown/Error'}")
    print(f"Expected head revision:    {head or 'Unknown/Error'}")
    print("-" * 60)
    
    if not current:
        print("\n⚠️  Could not determine current database revision.")
        print("This usually means:")
        print("  1. The database is not initialized (alembic_version table missing)")
        print("  2. Database connection failed")
        print("  3. The revision in the database doesn't exist in the codebase")
        print("\nRecommended action: Run with --stamp to set the current head")
        sys.exit(1)
    elif not head:
        print("\n❌ Could not determine head revision from codebase.")
        print("This is a critical error. Please check your alembic configuration.")
        sys.exit(1)
    elif current == head:
        print("\n✅ Database is at the current head revision. No action needed.")
        sys.exit(0)
    else:
        print(f"\n⚠️  Database revision mismatch!")
        print(f"   Database is at: {current}")
        print(f"   Head is at:     {head}")
        print("\nRecommended action: Run with --stamp to update the database")
        sys.exit(1)


def stamp_revision(force: bool = False) -> None:
    """Stamp the database to the current head."""
    print("Stamping database to current head...")
    print("-" * 60)
    
    if not force:
        print("Performing pre-flight checks...")
        head = get_head_revision()
        if not head:
            print("❌ Could not determine head revision. Use --force-stamp to skip checks.")
            sys.exit(1)
        print(f"Target head revision: {head}")
    
    print("\n⚠️  WARNING: This will update the alembic_version table in your database.")
    print("Make sure your database schema matches the expected state!")
    print("\nContinuing in 3 seconds... (Press Ctrl+C to cancel)")
    
    try:
        import time
        time.sleep(3)
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user.")
        sys.exit(1)
    
    print("\nExecuting: alembic stamp head")
    returncode, stdout, stderr = run_command(["alembic", "stamp", "head"], capture=False)
    
    if returncode == 0:
        print("\n✅ Successfully stamped database to current head!")
        print("\nVerifying...")
        check_revision()
    else:
        print(f"\n❌ Failed to stamp database: {stderr}")
        sys.exit(1)


def show_history() -> None:
    """Show the migration history."""
    print("Migration history:")
    print("-" * 60)
    returncode, stdout, stderr = run_command(["alembic", "history", "--verbose"], capture=False)
    if returncode != 0:
        print(f"❌ Error: {stderr}")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Helper script to fix Alembic migration revision errors",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --check           Check current database revision
  %(prog)s --stamp           Stamp database to current head (safe)
  %(prog)s --force-stamp     Force stamp without validation
  %(prog)s --history         Show migration history

For more information, see ALEMBIC_MIGRATION_RESET.md
        """,
    )
    
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check current database revision status",
    )
    parser.add_argument(
        "--stamp",
        action="store_true",
        help="Stamp database to current head revision",
    )
    parser.add_argument(
        "--force-stamp",
        action="store_true",
        help="Force stamp without validation (use with caution)",
    )
    parser.add_argument(
        "--history",
        action="store_true",
        help="Show migration history",
    )
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if not any([args.check, args.stamp, args.force_stamp, args.history]):
        parser.print_help()
        sys.exit(0)
    
    # Execute requested action
    if args.history:
        show_history()
    elif args.check:
        check_revision()
    elif args.stamp:
        stamp_revision(force=False)
    elif args.force_stamp:
        stamp_revision(force=True)


if __name__ == "__main__":
    main()
