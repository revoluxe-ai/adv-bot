# Alembic Migration Reset Guide

## Problem

If you encounter the error:
```
ERROR [alembic.util.messaging] Can't locate revision identified by '6941eea4ae8b'
FAILED: Can't locate revision identified by '6941eea4ae8b'
```

This means your database's `alembic_version` table contains a reference to a migration revision that no longer exists in the codebase.

## Root Cause

This repository's git history was grafted (squashed) at commit `4f4c1ca`, which removed all previous migration history. However, existing databases may still reference old revision IDs like `6941eea4ae8b`.

## Solution

You have two options to fix this:

### Option 1: Stamp Database to Current Head (Recommended)

This option assumes your database schema is already up-to-date and you just need to update the version tracking.

1. **Check your current database schema** - Make sure it matches the expected schema

2. **Stamp the database to the current head:**
   ```bash
   # If using Poetry (recommended for this project)
   poetry run alembic stamp head
   
   # Or if alembic is in your PATH
   alembic stamp head
   ```

3. **Verify the stamp worked:**
   ```bash
   poetry run alembic current
   # or
   alembic current
   ```
   You should see: `6eb95f5a8c66 (head)`

4. **Now you can create new migrations:**
   ```bash
   poetry run alembic revision --autogenerate -m "Your migration message"
   # or
   alembic revision --autogenerate -m "Your migration message"
   ```

### Option 2: Reset and Re-apply All Migrations

This option is safer if you're unsure about your database state, but requires downtime.

**⚠️ WARNING: This will drop and recreate your database schema. Back up your data first!**

1. **Backup your database:**
   ```bash
   pg_dump -U postgres adv_bot > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Drop the alembic_version table:**
   ```sql
   DROP TABLE IF EXISTS alembic_version;
   ```

3. **Run all migrations from scratch:**
   ```bash
   # If using Poetry
   poetry run alembic upgrade head
   
   # Or if alembic is in your PATH
   alembic upgrade head
   ```

4. **Verify:**
   ```bash
   poetry run alembic current
   # or
   alembic current
   ```

### Option 3: Manual Database Fix (Advanced)

If you need more control, you can manually update the alembic_version table:

1. **Connect to your database:**
   ```bash
   psql -U postgres -d adv_bot
   ```

2. **Check current version:**
   ```sql
   SELECT * FROM alembic_version;
   ```

3. **Update to the current head:**
   ```sql
   UPDATE alembic_version SET version_num = '6eb95f5a8c66';
   ```

4. **Exit and verify:**
   ```bash
   poetry run alembic current
   # or
   alembic current
   ```

## Current Migration Head

The current head revision in this repository is: **`6eb95f5a8c66`**

You can verify this with:
```bash
poetry run alembic heads
# or
alembic heads
```

## Migration Chain

The current migration chain (from oldest to newest) is:

```
Root branches:
├── 0cf5b8a2edf8 (add_auto_add_only_relevant_phrase_in_)
└── 30d489ece148 (add_shop_id_to_wbtoken)
    └── 42cfd1a692b5 (add_shop_id_index_to_wbtoken)
        └── 563a95f2f3bb (add_auto_update_white_list_to_advsetting)
            └── 3a55768aa832 (add_relevant_to_keywordsetting)
                └── 5eb707e93aa0 (add_auto_update_target_place_in_)
                    └── ab95fca5744f (add_index_to_wbcategory)
                        └── 2e38438b0f7e (add_max_balance_adding_for_day_and_auto_)

Merge point:
└── 3730e958b41e (merge: 0cf5b8a2edf8, 2e38438b0f7e)
    └── 89d25ba5dcd2 (sync_models_to_db)
        ├── 59c1dfb0c0ad (add_orders_source_for_auto_mode_to_)
        │   └── a689d49164e5 (add_predict_ctr_mode_to_advsetting)
        └── f8e1d9c2a3b4 (add_token_notification_tracker_table)

Final merge:
└── 6eb95f5a8c66 (merge: a689d49164e5, f8e1d9c2a3b4) ← HEAD
```

## Using the Helper Script

For convenience, you can use the provided helper script (requires Poetry to be installed):

```bash
# With Poetry
poetry run python scripts/reset_alembic.py --stamp

# Or directly if your environment is activated
python scripts/reset_alembic.py --stamp
```

This will automatically stamp your database to the current head.

## Validating Migration Chain

To ensure the migration files are consistent and valid, you can run:

```bash
python scripts/validate_migrations.py
```

This will check:
- All migrations have valid revision IDs
- All referenced parent revisions exist
- There's exactly one head revision
- No circular dependencies exist

## Prevention

To avoid this issue in the future:
1. Always keep your database's `alembic_version` in sync with the codebase
2. When pulling major changes that affect migrations, check `poetry run alembic current` vs `poetry run alembic heads`
3. Consider using `poetry run alembic stamp head` after major repository updates

## Getting Help

If you're still experiencing issues:
1. Check that your `alembic.ini` is configured correctly
2. Verify your database connection string in `alembic.ini` or environment variables
3. Run `poetry run alembic history --verbose` to see the full migration chain
4. Check if you have multiple heads with `poetry run alembic heads`
