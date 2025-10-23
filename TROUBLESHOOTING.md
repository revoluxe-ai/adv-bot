# Troubleshooting Common Issues

This document provides solutions to common issues you might encounter when working with this project.

## Table of Contents

1. [Alembic Migration Errors](#alembic-migration-errors)
2. [Database Connection Issues](#database-connection-issues)
3. [Environment Setup](#environment-setup)

---

## Alembic Migration Errors

### Error: "Can't locate revision identified by '6941eea4ae8b'"

**Symptoms:**
```
ERROR [alembic.util.messaging] Can't locate revision identified by '6941eea4ae8b'
FAILED: Can't locate revision identified by '6941eea4ae8b'
```

**Cause:**  
Your database's `alembic_version` table references an old migration revision that no longer exists in the codebase (due to repository history being grafted).

**Quick Fix:**
```bash
# Option 1: Use the helper script (recommended)
poetry run python scripts/reset_alembic.py --check   # Check current status
poetry run python scripts/reset_alembic.py --stamp   # Fix the issue

# Option 2: Manual fix
poetry run alembic stamp head
# or if alembic is in your PATH
alembic stamp head
```

**Detailed Guide:**  
See [ALEMBIC_MIGRATION_RESET.md](./ALEMBIC_MIGRATION_RESET.md) for comprehensive instructions.

### Error: "Multiple heads detected"

**Symptoms:**
```
ERROR: Only a single head is supported. Multiple heads found
```

**Fix:**
```bash
# Check which heads exist
poetry run alembic heads

# Merge the heads (Alembic will create a merge migration)
poetry run alembic merge -m "merge heads" <rev1> <rev2>

# Or stamp to a specific revision
poetry run alembic stamp <revision_id>
```

### Error: "Can't connect to database"

**Check:**
1. Database is running
2. Connection string in `alembic.ini` is correct
3. Environment variables are set (check `.env` file)
4. Database exists: `createdb adv_bot` (if using PostgreSQL)

---

## Database Connection Issues

### PostgreSQL Connection Failed

**Check these:**
```bash
# 1. PostgreSQL is running
sudo systemctl status postgresql
# or on macOS
brew services list | grep postgres

# 2. Test connection
psql -U postgres -d adv_bot -c "SELECT version();"

# 3. Check environment variables
echo $DATABASE_URL
```

**Common fixes:**
- Start PostgreSQL: `sudo systemctl start postgresql`
- Create database: `createdb adv_bot`
- Update connection string in `.env` or `alembic.ini`

---

## Environment Setup

### Missing Python Dependencies

**Fix:**
```bash
# Using poetry (recommended)
poetry install

# Using pip
pip install -r requirements.txt
```

### Missing Environment Variables

**Create `.env` file from template:**
```bash
cp env.sample .env
# Edit .env with your values
```

**Required variables:**
- `DATABASE_URL` - PostgreSQL connection string
- `TELEGRAM_BOT_TOKEN` - Your bot token
- See `env.sample` for complete list

---

## Getting More Help

If you're still experiencing issues:

1. **Check existing documentation:**
   - [START_HERE.md](./START_HERE.md) - Quick start guide
   - [ALEMBIC_MIGRATION_RESET.md](./ALEMBIC_MIGRATION_RESET.md) - Migration issues
   - Project documentation in `docs/` folder

2. **Enable debug logging:**
   ```python
   # In your code or config
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

3. **Check recent changes:**
   ```bash
   git log --oneline -10
   ```

4. **Verify system requirements:**
   - Python 3.12+
   - PostgreSQL 13+
   - Required system packages

---

## Quick Command Reference

```bash
# Database migrations
poetry run alembic current              # Show current revision
poetry run alembic heads                # Show head revisions
poetry run alembic history              # Show migration history
poetry run alembic upgrade head         # Apply all migrations
poetry run alembic stamp head           # Mark database as up-to-date
poetry run python scripts/reset_alembic.py --check  # Check migration status

# Database access
psql -U postgres -d adv_bot  # Connect to database
pg_dump adv_bot > backup.sql # Backup database

# Environment
python --version             # Check Python version
poetry --version             # Check Poetry version
```
