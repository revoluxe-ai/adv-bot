-- ============================================================================
-- 002_application_security_cutover.sql
-- ============================================================================
-- Назначение: постоянный APPLICATION_SECURITY_CUTOVER (Owner GO).
-- Таблица(и)/объекты: public app objects → owner app_owner; runtime advupdater DML-only.
-- Параметры: нет
-- Вызывается: после forensics; до финального APPLICATION fingerprint.
-- Зависимости Zalando: роли app_owner / app_migrator и databases.owner
--   должны быть согласованы с postgresql CR (иначе operator откатит).
-- ============================================================================

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_owner') THEN
    CREATE ROLE app_owner NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_migrator') THEN
    CREATE ROLE app_migrator LOGIN NOINHERIT;
  END IF;
END $$;

-- app_migrator → единственный штатный SET ROLE app_owner (NOINHERIT).
GRANT app_owner TO app_migrator WITH INHERIT FALSE, SET TRUE;

-- Ownership transfer (current DB only).
REASSIGN OWNED BY advupdater TO app_owner;

-- Database / schema ownership for CREATE control (PG15+ pg_database_owner).
ALTER DATABASE adv_updater OWNER TO app_owner;

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM advupdater;
GRANT USAGE ON SCHEMA public TO advupdater;
GRANT USAGE ON SCHEMA public TO app_migrator;

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO advupdater;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO advupdater;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app_migrator;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_migrator;

ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO advupdater;
ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO advupdater;

-- B2c: runtime must not be SUPERUSER (Zalando CR must also drop the flag).
ALTER ROLE advupdater NOSUPERUSER;
ALTER ROLE advupdater NOCREATEDB;

-- Hardening: migrator should not inherit app_owner privileges implicitly.
ALTER ROLE app_migrator NOINHERIT;
ALTER ROLE app_owner NOLOGIN;
