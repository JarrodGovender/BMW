CREATE TABLE public.doc_expenses (
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
