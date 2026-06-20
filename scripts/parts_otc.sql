CREATE TABLE public.parts_otc (
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
