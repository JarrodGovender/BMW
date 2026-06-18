CREATE TABLE public.deal_desk (
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
