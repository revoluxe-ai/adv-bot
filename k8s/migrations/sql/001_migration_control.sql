-- ============================================================================
-- 001_migration_control.sql
-- ============================================================================
-- Назначение: control-plane schema для lease/fencing и SECURITY DEFINER transitions.
-- Таблица(и): migration_control.release_lease, migration_control.release_execution,
--             migration_control.baseline_registry
-- Параметры: нет (bootstrap DDL)
-- Вызывается: Owner GO / Control Job bootstrap (не app runtime)
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS migration_control;

CREATE TABLE IF NOT EXISTS migration_control.release_lease (
    id              integer PRIMARY KEY CHECK (id = 1),
    release_id      text,
    fencing_token   bigint NOT NULL DEFAULT 0,
    workflow_run_id text,
    lease_expires_at timestamptz,
    updated_at      timestamptz NOT NULL DEFAULT now()
);

INSERT INTO migration_control.release_lease (id, fencing_token)
VALUES (1, 0)
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS migration_control.release_execution (
    release_id              text PRIMARY KEY,
    fencing_token           bigint NOT NULL,
    workflow_run_id         text NOT NULL,
    image_digest            text NOT NULL,
    source_revision_set     jsonb NOT NULL,
    target_revision         text NOT NULL,
    migration_state         text NOT NULL
        CHECK (migration_state IN (
            'NOT_STARTED', 'RUNNING', 'SUCCEEDED', 'NOOP',
            'PARTIAL_OR_UNKNOWN', 'RECONCILIATION_REQUIRED'
        )),
    deployment_state        text NOT NULL
        CHECK (deployment_state IN (
            'NOT_STARTED', 'DEPLOYING', 'COMPLETED', 'ABORTED'
        )),
    lease_expires_at        timestamptz,
    started_at              timestamptz NOT NULL DEFAULT now(),
    migration_completed_at  timestamptz,
    deployment_completed_at timestamptz,
    pod_uid                 text,
    kubernetes_job_name     text,
    diagnostic_payload      jsonb,
    updated_at              timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS migration_control.baseline_registry (
    baseline_id                     text PRIMARY KEY,
    database_identity               text NOT NULL,
    database_name                   text NOT NULL,
    postgres_major                  text NOT NULL,
    schema_scope                    text NOT NULL,
    canonical_revision_set          jsonb NOT NULL,
    source_history_hash             text NOT NULL,
    expected_schema_manifest_hash   text,
    actual_schema_manifest_hash     text,
    fingerprint_algorithm_version   text NOT NULL DEFAULT '1',
    status                          text NOT NULL DEFAULT 'RECONCILED',
    approved_exceptions             jsonb NOT NULL DEFAULT '[]'::jsonb,
    approved_at                     timestamptz,
    owner_approval_reference        text,
    UNIQUE (database_identity, schema_scope)
);

CREATE OR REPLACE FUNCTION migration_control.acquire_or_get_release(
    p_release_id text,
    p_workflow_run_id text,
    p_image_digest text,
    p_source_revision_set jsonb,
    p_target_revision text,
    p_lease_expires_at timestamptz
) RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = migration_control, pg_temp
AS $$
DECLARE
    v_lease migration_control.release_lease%ROWTYPE;
    v_exec migration_control.release_execution%ROWTYPE;
    v_token bigint;
BEGIN
    SELECT * INTO v_lease
    FROM migration_control.release_lease
    WHERE id = 1
    FOR UPDATE;

    SELECT * INTO v_exec
    FROM migration_control.release_execution
    WHERE release_id = p_release_id;

    IF FOUND THEN
        IF v_exec.workflow_run_id = p_workflow_run_id
           AND v_exec.image_digest = p_image_digest
           AND v_exec.target_revision = p_target_revision THEN
            RETURN jsonb_build_object(
                'status', 'IDEMPOTENT_HIT',
                'release_id', v_exec.release_id,
                'fencing_token', v_exec.fencing_token,
                'migration_state', v_exec.migration_state,
                'deployment_state', v_exec.deployment_state
            );
        END IF;
        RAISE EXCEPTION 'PRECONDITION_FAILED: release_id exists with different binding';
    END IF;

    IF v_lease.release_id IS NOT NULL
       AND v_lease.lease_expires_at IS NOT NULL
       AND v_lease.lease_expires_at > now()
       AND v_lease.release_id IS DISTINCT FROM p_release_id THEN
        RAISE EXCEPTION 'PRECONDITION_FAILED: active lease held by %', v_lease.release_id;
    END IF;

    v_token := v_lease.fencing_token + 1;
    UPDATE migration_control.release_lease
    SET fencing_token = v_token,
        release_id = p_release_id,
        workflow_run_id = p_workflow_run_id,
        lease_expires_at = p_lease_expires_at,
        updated_at = now()
    WHERE id = 1;

    INSERT INTO migration_control.release_execution (
        release_id, fencing_token, workflow_run_id, image_digest,
        source_revision_set, target_revision,
        migration_state, deployment_state, lease_expires_at
    ) VALUES (
        p_release_id, v_token, p_workflow_run_id, p_image_digest,
        p_source_revision_set, p_target_revision,
        'NOT_STARTED', 'NOT_STARTED', p_lease_expires_at
    );

    RETURN jsonb_build_object(
        'status', 'ACQUIRED',
        'release_id', p_release_id,
        'fencing_token', v_token,
        'migration_state', 'NOT_STARTED',
        'deployment_state', 'NOT_STARTED'
    );
END;
$$;

CREATE OR REPLACE FUNCTION migration_control._require_token(
    p_release_id text,
    p_fencing_token bigint
) RETURNS migration_control.release_execution
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = migration_control, pg_temp
AS $$
DECLARE
    v_exec migration_control.release_execution%ROWTYPE;
    v_lease migration_control.release_lease%ROWTYPE;
BEGIN
    SELECT * INTO v_lease FROM migration_control.release_lease WHERE id = 1 FOR UPDATE;
    IF v_lease.release_id IS DISTINCT FROM p_release_id
       OR v_lease.fencing_token IS DISTINCT FROM p_fencing_token THEN
        RAISE EXCEPTION 'PRECONDITION_FAILED: stale fencing token';
    END IF;
    SELECT * INTO v_exec FROM migration_control.release_execution WHERE release_id = p_release_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'PRECONDITION_FAILED: unknown release_id';
    END IF;
    IF v_exec.fencing_token IS DISTINCT FROM p_fencing_token THEN
        RAISE EXCEPTION 'PRECONDITION_FAILED: execution fencing mismatch';
    END IF;
    RETURN v_exec;
END;
$$;

CREATE OR REPLACE FUNCTION migration_control.mark_migration_started(
    p_release_id text, p_fencing_token bigint, p_pod_uid text DEFAULT NULL
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = migration_control, pg_temp
AS $$
DECLARE v_exec migration_control.release_execution%ROWTYPE;
BEGIN
    v_exec := migration_control._require_token(p_release_id, p_fencing_token);
    IF v_exec.migration_state <> 'NOT_STARTED' THEN
        RAISE EXCEPTION 'PRECONDITION_FAILED: migration_state=%', v_exec.migration_state;
    END IF;
    UPDATE migration_control.release_execution
    SET migration_state = 'RUNNING', pod_uid = COALESCE(p_pod_uid, pod_uid), updated_at = now()
    WHERE release_id = p_release_id;
    RETURN jsonb_build_object('migration_state', 'RUNNING');
END;
$$;

CREATE OR REPLACE FUNCTION migration_control.mark_migration_succeeded(
    p_release_id text, p_fencing_token bigint
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = migration_control, pg_temp
AS $$
DECLARE v_exec migration_control.release_execution%ROWTYPE;
BEGIN
    v_exec := migration_control._require_token(p_release_id, p_fencing_token);
    IF v_exec.migration_state <> 'RUNNING' THEN
        RAISE EXCEPTION 'PRECONDITION_FAILED: migration_state=% (need RUNNING)', v_exec.migration_state;
    END IF;
    UPDATE migration_control.release_execution
    SET migration_state = 'SUCCEEDED', migration_completed_at = now(), updated_at = now()
    WHERE release_id = p_release_id;
    RETURN jsonb_build_object('migration_state', 'SUCCEEDED');
END;
$$;

CREATE OR REPLACE FUNCTION migration_control.mark_migration_noop(
    p_release_id text, p_fencing_token bigint
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = migration_control, pg_temp
AS $$
DECLARE v_exec migration_control.release_execution%ROWTYPE;
BEGIN
    v_exec := migration_control._require_token(p_release_id, p_fencing_token);
    IF v_exec.migration_state <> 'RUNNING' THEN
        RAISE EXCEPTION 'PRECONDITION_FAILED: migration_state=% (need RUNNING)', v_exec.migration_state;
    END IF;
    UPDATE migration_control.release_execution
    SET migration_state = 'NOOP', migration_completed_at = now(), updated_at = now()
    WHERE release_id = p_release_id;
    RETURN jsonb_build_object('migration_state', 'NOOP');
END;
$$;

CREATE OR REPLACE FUNCTION migration_control.mark_migration_unknown(
    p_release_id text, p_fencing_token bigint, p_diagnostic jsonb DEFAULT '{}'::jsonb
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = migration_control, pg_temp
AS $$
DECLARE v_exec migration_control.release_execution%ROWTYPE;
BEGIN
    v_exec := migration_control._require_token(p_release_id, p_fencing_token);
    -- Only RUNNING may become PARTIAL_OR_UNKNOWN (never downgrade SUCCEEDED/NOOP).
    IF v_exec.migration_state <> 'RUNNING' THEN
        RAISE EXCEPTION 'PRECONDITION_FAILED: migration_state=% (need RUNNING)', v_exec.migration_state;
    END IF;
    UPDATE migration_control.release_execution
    SET migration_state = 'PARTIAL_OR_UNKNOWN',
        diagnostic_payload = p_diagnostic,
        updated_at = now()
    WHERE release_id = p_release_id;
    RETURN jsonb_build_object('migration_state', 'PARTIAL_OR_UNKNOWN');
END;
$$;

CREATE OR REPLACE FUNCTION migration_control.acquire_reconciliation_lease(
    p_release_id text,
    p_workflow_run_id text,
    p_lease_expires_at timestamptz
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = migration_control, pg_temp
AS $$
DECLARE
    v_lease migration_control.release_lease%ROWTYPE;
    v_exec migration_control.release_execution%ROWTYPE;
    v_token bigint;
BEGIN
    SELECT * INTO v_lease FROM migration_control.release_lease WHERE id = 1 FOR UPDATE;
    SELECT * INTO v_exec FROM migration_control.release_execution WHERE release_id = p_release_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'PRECONDITION_FAILED: unknown release';
    END IF;
    IF v_exec.deployment_state = 'COMPLETED' THEN
        RAISE EXCEPTION 'PRECONDITION_FAILED: release already COMPLETED';
    END IF;
    IF v_lease.lease_expires_at IS NOT NULL AND v_lease.lease_expires_at > now() THEN
        RAISE EXCEPTION 'PRECONDITION_FAILED: lease not expired';
    END IF;
    IF v_lease.release_id IS DISTINCT FROM p_release_id THEN
        RAISE EXCEPTION 'PRECONDITION_FAILED: lease owner mismatch';
    END IF;
    v_token := v_lease.fencing_token + 1;
    UPDATE migration_control.release_lease
    SET fencing_token = v_token,
        workflow_run_id = p_workflow_run_id,
        lease_expires_at = p_lease_expires_at,
        updated_at = now()
    WHERE id = 1;
    UPDATE migration_control.release_execution
    SET fencing_token = v_token,
        migration_state = 'RECONCILIATION_REQUIRED',
        workflow_run_id = p_workflow_run_id,
        lease_expires_at = p_lease_expires_at,
        updated_at = now()
    WHERE release_id = p_release_id;
    RETURN jsonb_build_object(
        'status', 'RECONCILE_ACQUIRED',
        'fencing_token', v_token,
        'migration_state', 'RECONCILIATION_REQUIRED'
    );
END;
$$;

CREATE OR REPLACE FUNCTION migration_control.begin_deployment(
    p_release_id text, p_fencing_token bigint
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = migration_control, pg_temp
AS $$
DECLARE v_exec migration_control.release_execution%ROWTYPE;
BEGIN
    v_exec := migration_control._require_token(p_release_id, p_fencing_token);
    IF v_exec.migration_state NOT IN ('SUCCEEDED', 'NOOP') THEN
        RAISE EXCEPTION 'PRECONDITION_FAILED: migration_state=%', v_exec.migration_state;
    END IF;
    UPDATE migration_control.release_execution
    SET deployment_state = 'DEPLOYING', updated_at = now()
    WHERE release_id = p_release_id;
    RETURN jsonb_build_object('deployment_state', 'DEPLOYING');
END;
$$;

CREATE OR REPLACE FUNCTION migration_control.complete_release(
    p_release_id text, p_fencing_token bigint
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = migration_control, pg_temp
AS $$
DECLARE v_exec migration_control.release_execution%ROWTYPE;
BEGIN
    v_exec := migration_control._require_token(p_release_id, p_fencing_token);
    IF v_exec.migration_state NOT IN ('SUCCEEDED', 'NOOP') THEN
        RAISE EXCEPTION 'PRECONDITION_FAILED: migration_state=% (need SUCCEEDED|NOOP)', v_exec.migration_state;
    END IF;
    IF v_exec.deployment_state <> 'DEPLOYING' THEN
        RAISE EXCEPTION 'PRECONDITION_FAILED: deployment_state=% (need DEPLOYING)', v_exec.deployment_state;
    END IF;
    UPDATE migration_control.release_execution
    SET deployment_state = 'COMPLETED',
        deployment_completed_at = now(),
        updated_at = now()
    WHERE release_id = p_release_id;
    UPDATE migration_control.release_lease
    SET release_id = NULL,
        workflow_run_id = NULL,
        lease_expires_at = NULL,
        updated_at = now()
    WHERE id = 1
      AND release_id = p_release_id
      AND fencing_token = p_fencing_token;
    RETURN jsonb_build_object('deployment_state', 'COMPLETED', 'lease', 'released');
END;
$$;

CREATE OR REPLACE FUNCTION migration_control.abort_deployment(
    p_release_id text, p_fencing_token bigint, p_diagnostic jsonb DEFAULT '{}'::jsonb
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = migration_control, pg_temp
AS $$
BEGIN
    PERFORM migration_control._require_token(p_release_id, p_fencing_token);
    UPDATE migration_control.release_execution
    SET deployment_state = 'ABORTED',
        diagnostic_payload = p_diagnostic,
        updated_at = now()
    WHERE release_id = p_release_id;
    RETURN jsonb_build_object('deployment_state', 'ABORTED');
END;
$$;

CREATE OR REPLACE FUNCTION migration_control.verify_baseline_and_acquire_release(
    p_release_id text,
    p_workflow_run_id text,
    p_image_digest text,
    p_source_revision_set jsonb,
    p_target_revision text,
    p_lease_expires_at timestamptz,
    p_database_identity text,
    p_source_history_hash text
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = migration_control, pg_temp
AS $$
DECLARE
    v_baseline migration_control.baseline_registry%ROWTYPE;
BEGIN
    SELECT * INTO v_baseline
    FROM migration_control.baseline_registry
    WHERE database_identity = p_database_identity
      AND schema_scope = 'APPLICATION'
      AND status = 'RECONCILED';
    IF NOT FOUND THEN
        RAISE EXCEPTION 'BASELINE_PRECONDITION_FAILED: no RECONCILED APPLICATION baseline';
    END IF;
    IF v_baseline.source_history_hash IS DISTINCT FROM p_source_history_hash THEN
        RAISE EXCEPTION 'BASELINE_PRECONDITION_FAILED: source_history_hash mismatch';
    END IF;
    RETURN migration_control.acquire_or_get_release(
        p_release_id, p_workflow_run_id, p_image_digest,
        p_source_revision_set, p_target_revision, p_lease_expires_at
    );
END;
$$;

REVOKE ALL ON FUNCTION migration_control.acquire_or_get_release(text, text, text, jsonb, text, timestamptz) FROM PUBLIC;
REVOKE ALL ON FUNCTION migration_control.mark_migration_started(text, bigint, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION migration_control.mark_migration_succeeded(text, bigint) FROM PUBLIC;
REVOKE ALL ON FUNCTION migration_control.mark_migration_noop(text, bigint) FROM PUBLIC;
REVOKE ALL ON FUNCTION migration_control.mark_migration_unknown(text, bigint, jsonb) FROM PUBLIC;
REVOKE ALL ON FUNCTION migration_control.acquire_reconciliation_lease(text, text, timestamptz) FROM PUBLIC;
REVOKE ALL ON FUNCTION migration_control.begin_deployment(text, bigint) FROM PUBLIC;
REVOKE ALL ON FUNCTION migration_control.complete_release(text, bigint) FROM PUBLIC;
REVOKE ALL ON FUNCTION migration_control.abort_deployment(text, bigint, jsonb) FROM PUBLIC;
REVOKE ALL ON FUNCTION migration_control.verify_baseline_and_acquire_release(text, text, text, jsonb, text, timestamptz, text, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION migration_control._require_token(text, bigint) FROM PUBLIC;

-- Role grants are applied by Owner after CREATE ROLE app_migrator / release_controller / app_owner.
-- GRANT EXECUTE ON FUNCTION ... TO release_controller;
-- GRANT EXECUTE ON FUNCTION mark_migration_* TO app_migrator;
