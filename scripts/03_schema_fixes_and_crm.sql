-- ============================================================================
-- 03_schema_fixes_and_crm.sql
-- Run this in the Supabase SQL Editor (Project > SQL Editor > New Query).
--
-- Fixes two live schema-drift errors the app is currently throwing:
--   PGRST205 ("Could not find table 'public.parts_otc'/'public.doc_expenses'
--             in the schema cache") -- the tables were never created in this
--             Supabase project, even though parts_otc.sql / doc_expenses.sql
--             already exist at the repo root describing the intended schema.
--   42703    ("column fi_vaps_revenue does not exist") -- the live deal_desk
--             table predates that column being added to deal_desk.sql.
--
-- All statements are idempotent (IF NOT EXISTS / ADD COLUMN IF NOT EXISTS)
-- so this script is safe to re-run.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1. PARTS_OTC -- mirrors parts_otc.sql exactly (columns used by
--    views/route_a_service.py's OTC capture form + command_center.py's
--    God Mode rollup).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.parts_otc (
    id serial PRIMARY KEY,
    invoice_number VARCHAR,
    client_name VARCHAR,
    parts_description TEXT,
    capital_cost NUMERIC,
    retail_price NUMERIC,
    net_profit NUMERIC,
    salesperson VARCHAR,
    location_id VARCHAR,
    department_id VARCHAR,
    brand_id VARCHAR,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- 2. DOC_EXPENSES -- mirrors doc_expenses.sql exactly (columns used by
--    views/route_b_sales.py's overhead capture form + command_center.py).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.doc_expenses (
    id serial PRIMARY KEY,
    expense_month VARCHAR,
    expense_category VARCHAR,
    amount NUMERIC,
    logged_by VARCHAR,
    location_id VARCHAR,
    department_id VARCHAR,
    brand_id VARCHAR,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- 3. DEAL_DESK -- create if entirely missing (matches deal_desk.sql), then
--    add the specific column that's missing on the live table if the table
--    already exists. Both statements are no-ops if already correct.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.deal_desk (
    id serial PRIMARY KEY,
    deal_source VARCHAR,
    client_name VARCHAR,
    vehicle_vsb VARCHAR,
    vehicle_desc VARCHAR,
    capital_cost NUMERIC,
    retail_price NUMERIC,
    fi_vaps_revenue NUMERIC,
    net_retained_profit NUMERIC,
    created_by VARCHAR,
    location_id VARCHAR,
    department_id VARCHAR,
    brand_id VARCHAR,
    created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.deal_desk ADD COLUMN IF NOT EXISTS fi_vaps_revenue NUMERIC;

-- ---------------------------------------------------------------------------
-- 4. CRM_LEADS -- Phase VI Cadence Engine.
--
-- Note on estimated_value: not in the original column list, but added here
-- because the CRM frontend's "Pipeline Value" metric (views/route_d_crm.py)
-- needs a monetary figure per lead and none of the listed columns provide
-- one -- without it, "Pipeline Value" has nothing to sum.
--
-- Note on assigned_exec: every other table in this schema (leads,
-- individual_leads, tender_leads, deal_desk.created_by, parts_otc.salesperson,
-- doc_expenses.logged_by) stores the *username* string, never a users.id
-- UUID -- there is no Supabase Auth session in this app (auth_view.py does
-- its own username/password check against public.users), so there's no
-- auth.uid() to key off either. assigned_exec is therefore TEXT storing
-- users.username, matching the existing "assigned_to" convention in
-- route_b_sales.py, rather than a UUID FK to a column that isn't actually
-- used as a join key anywhere else in this codebase.
--
-- location_id/department_id/brand_id naming matches every other table here
-- (leads, deal_desk, parts_otc, doc_expenses, service_wip, users) instead of
-- a bare "location" column, so apply_matrix_filters()/apply_location_matrix_filters()
-- in views/shared_utils.py work against crm_leads without a one-off exception.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.crm_leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_name TEXT NOT NULL,
    contact_number TEXT,
    vehicle_of_interest TEXT,
    source TEXT,
    status TEXT NOT NULL DEFAULT 'New'
        CHECK (status IN ('New', 'Contacted', 'Test Drive', 'Negotiation', 'Closed')),
    temperature TEXT NOT NULL DEFAULT 'Warm'
        CHECK (temperature IN ('Cold', 'Warm', 'Hot')),
    last_contact TIMESTAMPTZ,
    next_action_due TIMESTAMPTZ,
    estimated_value NUMERIC DEFAULT 0,
    assigned_exec TEXT,
    location_id VARCHAR,
    department_id VARCHAR,
    brand_id VARCHAR,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_crm_leads_location ON public.crm_leads (location_id);
CREATE INDEX IF NOT EXISTS idx_crm_leads_assigned_exec ON public.crm_leads (assigned_exec);
CREATE INDEX IF NOT EXISTS idx_crm_leads_next_action_due ON public.crm_leads (next_action_due);

-- ---------------------------------------------------------------------------
-- 5. ROW LEVEL SECURITY
--
-- This app's access control (apply_matrix_filters / apply_location_matrix_filters
-- in views/shared_utils.py) is enforced entirely in Python against
-- st.session_state, using the Supabase client configured in config.py with
-- the project key from .streamlit/secrets.toml -- there is no Supabase Auth
-- session, so policies written against auth.uid()/auth.jwt() would match
-- nothing and (with RLS enabled) silently lock the app out of its own table.
-- Enabling RLS with a permissive policy for anon+authenticated keeps the
-- table consistent with "RLS is on" while not breaking the only access path
-- this app actually has. Tighten this later only if/when real Supabase Auth
-- sessions are introduced.
-- ---------------------------------------------------------------------------
ALTER TABLE public.crm_leads ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "crm_leads_select_all" ON public.crm_leads;
CREATE POLICY "crm_leads_select_all" ON public.crm_leads
    FOR SELECT TO anon, authenticated USING (true);

DROP POLICY IF EXISTS "crm_leads_insert_all" ON public.crm_leads;
CREATE POLICY "crm_leads_insert_all" ON public.crm_leads
    FOR INSERT TO anon, authenticated WITH CHECK (true);

DROP POLICY IF EXISTS "crm_leads_update_all" ON public.crm_leads;
CREATE POLICY "crm_leads_update_all" ON public.crm_leads
    FOR UPDATE TO anon, authenticated USING (true) WITH CHECK (true);

DROP POLICY IF EXISTS "crm_leads_delete_all" ON public.crm_leads;
CREATE POLICY "crm_leads_delete_all" ON public.crm_leads
    FOR DELETE TO anon, authenticated USING (true);
