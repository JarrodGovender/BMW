-- ============================================================================
-- 04_soc_telemetry_and_access_control.sql
-- Run this in the Supabase SQL Editor (Project > SQL Editor > New Query).
--
-- Adds the schema COMMAND 30 (Super User SOC, Telemetry & Property
-- Management) depends on. None of these existed on the live schema before:
--   users.last_active_timestamp -- views/admin_telemetry.py's 5-minute
--       active-users heartbeat (utils/telemetry.py).
--   users.force_logout / users.is_revoked -- views/admin_users.py's
--       session-termination toggles, enforced in app.py + views/auth_view.py.
--   property_notes -- views/admin_properties.py's site-level visit/audit
--       log (distinct from the existing task-level task_notes table).
--
-- All statements are idempotent (ADD COLUMN IF NOT EXISTS / CREATE TABLE IF
-- NOT EXISTS) so this script is safe to re-run. Until it's applied, the
-- corresponding admin features fail soft (caught exceptions / empty tables)
-- rather than crashing the app.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. USERS -- SOC heartbeat + session control columns.
-- ---------------------------------------------------------------------------
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS last_active_timestamp TIMESTAMPTZ;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS force_logout BOOLEAN DEFAULT false;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS is_revoked BOOLEAN DEFAULT false;

-- ---------------------------------------------------------------------------
-- 2. PROPERTY_NOTES -- site-level audit/visit log (views/admin_properties.py).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.property_notes (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    site_id BIGINT REFERENCES public.property_sites(id) ON DELETE CASCADE,
    note_text TEXT NOT NULL,
    author_name VARCHAR,
    created_at TIMESTAMPTZ DEFAULT now()
);
