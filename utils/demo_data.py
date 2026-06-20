"""
Presentation/Demo data layer for the Command Center and departmental views.

Used whenever st.session_state['presentation_mode'] is True (the default --
see app.py), entirely bypassing Supabase so Exco/Dealer Principal demos
never show an empty table, an in-progress live figure, or a network error
mid-presentation.

Design note: rather than hand-writing separate "headline" numbers, this
module generates synthetic rows in the *same shape* as the real
used_car_stock / service_wip / deal_desk / parts_otc / doc_expenses tables.
views/command_center.py runs those synthetic rows through the exact same
aggregation code it uses for live data -- so every figure on the page
(podiums, Key Metrics tiles, the DOC gauge, the legacy rollup tables) is
derived from one consistent dataset, with no risk of a headline tile
disagreeing with a drill-down table during a live demo. Branch-level
targets below were tuned so the totals land on Total Revenue ~R214.6M,
Gross Profit ~R61.3M, and 312 Units Sold, and so the Stock Ageing donut's
5 buckets sum to 884 units -- matching the supplied mockup.

Granular layer (COMMAND 29): get_demo_vehicle_sales_records() /
get_demo_stockbook_records() / get_demo_wip_records() generate one row per
vehicle sale / stock unit / repair order, with VIN, make/model, branch and
sales-exec-level detail for Exco drill-downs. The aggregate functions below
(get_demo_deal_desk_rows / get_demo_stock_rows / get_demo_service_wip_rows)
now simply project the granular records down to the columns the Command
Center aggregation already expects -- so the headline tiles and the
departmental drill-down tables are mathematically guaranteed to agree;
they're reading the exact same underlying rows, not two independently
tuned datasets.
"""
import random
from datetime import datetime, timedelta

_SEED = 1337

DEALER_BRANCHES = [
    "BMW Sandton", "BMW Bedfordview", "MF Sandton",
    "BMW East Rand", "MF Fourways", "BMW Dalpark",
]

LOCATION_IDS = {
    "BMW Sandton": "BMW_SANDTON",
    "BMW Bedfordview": "BMW_BEDFORDVIEW",
    "MF Sandton": "MF_SANDTON",
    "BMW East Rand": "BMW_EASTRAND",
    "MF Fourways": "MF_FOURWAYS",
    "BMW Dalpark": "BMW_DALPARK",
}

# Per-branch demo targets. Vehicle/Parts/Service sums and Locked Units sum
# exactly to the Total Revenue / Units Sold headline tiles (171.92M + 16.06M
# + 26.62M = 214.6M; 78+64+52+47+39+32 = 312). Margins are tuned so
# Gross Profit (vehicle + parts net profit) lands at ~R61.3M / 28.6% blended
# -- on the rich end for vehicle margin alone, but defensible as "net
# retained profit" inclusive of F&I/finance income at a premium franchise.
BRANCH_TARGETS = {
    "BMW Sandton":     dict(vehicle_retail=47_920_000, vehicle_margin=0.360, parts_retail=4_580_000, service_closed=5_920_000, vaps=3_640_000, doc=2_140_000, stock_value=36_400_000, unencumbered_ratio=0.764, locked_units=78, open_wips=38, open_wip_value=2_140_000),
    "BMW Bedfordview": dict(vehicle_retail=33_800_000, vehicle_margin=0.340, parts_retail=3_360_000, service_closed=6_840_000, vaps=2_980_000, doc=1_780_000, stock_value=27_900_000, unencumbered_ratio=0.720, locked_units=64, open_wips=47, open_wip_value=2_600_000),
    "MF Sandton":      dict(vehicle_retail=27_600_000, vehicle_margin=0.330, parts_retail=2_740_000, service_closed=3_960_000, vaps=2_310_000, doc=1_310_000, stock_value=21_300_000, unencumbered_ratio=0.746, locked_units=52, open_wips=29, open_wip_value=1_500_000),
    "BMW East Rand":   dict(vehicle_retail=24_900_000, vehicle_margin=0.310, parts_retail=2_460_000, service_closed=4_780_000, vaps=2_080_000, doc=1_080_000, stock_value=18_700_000, unencumbered_ratio=0.706, locked_units=47, open_wips=32, open_wip_value=1_680_000),
    "MF Fourways":     dict(vehicle_retail=20_500_000, vehicle_margin=0.300, parts_retail=1_640_000, service_closed=2_980_000, vaps=1_720_000, doc=830_000,  stock_value=14_600_000, unencumbered_ratio=0.671, locked_units=39, open_wips=23, open_wip_value=1_130_000),
    "BMW Dalpark":     dict(vehicle_retail=17_200_000, vehicle_margin=0.277, parts_retail=1_280_000, service_closed=2_140_000, vaps=1_380_000, doc=610_000,  stock_value=11_200_000, unencumbered_ratio=0.616, locked_units=32, open_wips=18, open_wip_value=790_000),
}

OTC_MARGIN = 0.30

# Stock Ageing donut -- 5 tiers by unit count, summing to 884 (matches mockup).
STOCK_AGEING_BUCKETS = {"0-30": 412, "31-60": 248, "61-90": 134, "91-120": 61, "120+": 29}
BUCKET_DAY_RANGES = {"0-30": (1, 30), "31-60": (31, 60), "61-90": (61, 90), "91-120": (91, 120), "120+": (121, 220)}

# "ROs Closed Today" has no closed_at column in the real schema (it's a
# permanent N/A placeholder on live data) -- this is its presentation-mode-
# only stand-in value.
ROS_CLOSED_TODAY = 19
ROS_OPENED_TODAY_TOTAL = 24

DIVISION_MATRIX = [
    ("BMW Sandton", ["green", "green", "green", "green"]),
    ("BMW Bedfordview", ["green", "green", "amber", "green"]),
    ("MF Sandton", ["green", "amber", "green", "green"]),
    ("BMW East Rand", ["amber", "green", "green", "amber"]),
    ("MF Fourways", ["amber", "amber", "amber", "green"]),
    ("BMW Dalpark", ["red", "amber", "amber", "red"]),
]

# Vehicle parc used for granular VIN-level rows -- realistic franchise mix.
VEHICLE_MAKES_MODELS = [
    ("BMW", "118i"), ("BMW", "120i M Sport"), ("BMW", "320i"), ("BMW", "330i"),
    ("BMW", "M340i"), ("BMW", "520d"), ("BMW", "X1 sDrive18i"), ("BMW", "X3 xDrive20d"),
    ("BMW", "X5 xDrive40d"), ("BMW", "X7 xDrive40i"), ("BMW", "M3 Competition"),
    ("MINI", "Cooper S"), ("MINI", "Countryman"), ("MINI", "Clubman"),
]

SALES_EXEC_POOL = {
    "BMW Sandton": ["T. Naidoo", "K. van der Berg", "S. Mokoena", "R. Patel"],
    "BMW Bedfordview": ["L. Botha", "N. Dlamini", "C. Reddy"],
    "MF Sandton": ["J. Coetzee", "A. Khumalo"],
    "BMW East Rand": ["M. Joubert", "P. Sithole"],
    "MF Fourways": ["D. Govender", "F. Nkosi"],
    "BMW Dalpark": ["W. Smit", "Z. Mahlangu"],
}

SERVICE_ADVISOR_POOL = {
    "BMW Sandton": ["B. Adams", "S. Mahlangu"],
    "BMW Bedfordview": ["G. Pretorius", "T. Zulu"],
    "MF Sandton": ["R. Naidu"],
    "BMW East Rand": ["K. Moodley", "L. Fourie"],
    "MF Fourways": ["P. Mthembu"],
    "BMW Dalpark": ["H. Erasmus"],
}

TECHNICIAN_POOL = {
    "BMW Sandton": ["Tech A. Sithole", "Tech B. Mokoena", "Tech C. van Wyk"],
    "BMW Bedfordview": ["Tech D. Khoza", "Tech E. Steyn"],
    "MF Sandton": ["Tech F. Ndlovu"],
    "BMW East Rand": ["Tech G. Botha", "Tech H. Radebe"],
    "MF Fourways": ["Tech I. Cele"],
    "BMW Dalpark": ["Tech J. Venter"],
}


def _rng():
    return random.Random(_SEED)


def _split_exact(rng, total, n, jitter=0.35):
    """n positive float parts that sum exactly to `total`, with light jitter for realism."""
    if n <= 0:
        return []
    weights = [max(0.1, 1 + rng.uniform(-jitter, jitter)) for _ in range(n)]
    wsum = sum(weights)
    parts = [total * w / wsum for w in weights]
    parts[-1] += total - sum(parts)
    return parts


def _split_int_exact(rng, total, weights):
    """Integer split of `total` across len(weights) buckets, summing exactly to `total`."""
    n = len(weights)
    wsum = sum(weights) or 1
    raw = [total * w / wsum for w in weights]
    parts = [int(r) for r in raw]
    remainder = total - sum(parts)
    order = sorted(range(n), key=lambda i: raw[i] - parts[i], reverse=True)
    for i in range(remainder):
        parts[order[i % n]] += 1
    return parts


def _cached(key, generator):
    """Generate once per session and cache -- every page reads the identical
    rows so re-rendering a tab never reshuffles which exec/technician/VIN
    landed on which figure. Falls back to a fresh (still deterministic)
    generation outside a Streamlit run context, e.g. for standalone scripts."""
    try:
        import streamlit as st
    except ImportError:
        return generator()
    if key not in st.session_state:
        st.session_state[key] = generator()
    return st.session_state[key]


# ------------------------------------------------------------------
# Granular, transaction-level generators (COMMAND 29)
# ------------------------------------------------------------------

def get_demo_vehicle_sales_records():
    """One row per locked unit (312 total) -- VIN, make/model, branch, sales
    exec, retail price and net profit. Sums exactly to vehicle_retail /
    vaps / vehicle_margin*vehicle_retail per branch, by construction of
    _split_exact -- so get_demo_deal_desk_rows() below can never disagree
    with this ledger."""
    rng = _rng()
    records = []
    seq = 1
    for branch in DEALER_BRANCHES:
        t = BRANCH_TARGETS[branch]
        n = t['locked_units']
        retail_vals = _split_exact(rng, t['vehicle_retail'], n)
        vaps_vals = _split_exact(rng, t['vaps'], n)
        profit_vals = _split_exact(rng, t['vehicle_retail'] * t['vehicle_margin'], n)
        exec_pool = SALES_EXEC_POOL[branch]
        for retail, vaps, profit in zip(retail_vals, vaps_vals, profit_vals):
            make, model = rng.choice(VEHICLE_MAKES_MODELS)
            year = rng.randint(2021, 2026)
            vin = f"WBA{seq:07d}{rng.randint(0, 9)}"
            exec_name = rng.choice(exec_pool)
            capital_cost = max(0.0, retail + vaps - profit)
            records.append({
                "vin": vin, "vehicle_vsb": vin, "make": make, "model": model,
                "vehicle_desc": f"{year} {make} {model}",
                "branch": branch, "location_id": LOCATION_IDS[branch],
                "department_id": "USED_SALES", "brand_id": "BMW" if make == "BMW" else "MINI",
                "client_name": f"Client #{seq:04d}",
                "sales_exec": exec_name, "created_by": exec_name,
                "deal_source": "📥 Pipeline",
                "capital_cost": round(capital_cost, 2),
                "retail_price": round(retail, 2),
                "fi_vaps_revenue": round(vaps, 2),
                "net_retained_profit": round(profit, 2),
            })
            seq += 1
    return records


def get_demo_stockbook_records():
    """One row per stock unit (884 total) -- VIN, age bracket, days in stock,
    value -- exactly matching the Stock Ageing donut's bucket breakdown."""
    rng = _rng()
    records = []
    seq = 1
    stock_weights = [BRANCH_TARGETS[b]['stock_value'] for b in DEALER_BRANCHES]
    today = datetime.now()
    bucket_total = sum(STOCK_AGEING_BUCKETS.values())

    for bucket, total_units in STOCK_AGEING_BUCKETS.items():
        per_branch_units = _split_int_exact(rng, total_units, stock_weights)
        lo, hi = BUCKET_DAY_RANGES[bucket]
        for branch, n_units in zip(DEALER_BRANCHES, per_branch_units):
            if n_units == 0:
                continue
            t = BRANCH_TARGETS[branch]
            bucket_value = t['stock_value'] * (total_units / bucket_total)
            values = _split_exact(rng, bucket_value, n_units)
            for v in values:
                unencumbered = rng.random() < t['unencumbered_ratio']
                days = rng.randint(lo, hi)
                make, model = rng.choice(VEHICLE_MAKES_MODELS)
                year = rng.randint(2021, 2026)
                vin = f"WBS{seq:07d}{rng.randint(0, 9)}"
                records.append({
                    "vsb_no": f"V{seq:05d}", "vin": vin, "chassis_no": vin,
                    "description": f"{year} {make} {model}", "make": make, "model": model,
                    "into_stock": (today - timedelta(days=days)).strftime('%Y-%m-%d'),
                    "days_in_stock": days, "age_bracket": bucket,
                    "total_value": round(v, 2),
                    "location": branch, "location_id": LOCATION_IDS[branch],
                    "department_id": "USED_SALES", "brand_id": "BMW" if make == "BMW" else "MINI",
                    "floorplan_status": "UNENCUMBERED" if unencumbered else "ON FLOORPLAN",
                    "comments": "", "stock_type": "Used",
                })
                seq += 1
    return records


def get_demo_wip_records():
    """One row per repair order -- RO number, client, vehicle, advisor,
    technician, status. Open WIP rows sum to open_wip_value (with exactly
    ROS_OPENED_TODAY_TOTAL dated today); closed rows sum to service_closed --
    same totals get_demo_service_wip_rows() used to hand-roll, now derived
    from these granular records instead."""
    rng = _rng()
    records = []
    seq = 1
    now = datetime.now()
    today_counts = _split_int_exact(
        rng, ROS_OPENED_TODAY_TOTAL, [BRANCH_TARGETS[b]['open_wips'] for b in DEALER_BRANCHES]
    )

    for branch, today_n in zip(DEALER_BRANCHES, today_counts):
        t = BRANCH_TARGETS[branch]
        loc = LOCATION_IDS[branch]
        advisors = SERVICE_ADVISOR_POOL[branch]
        techs = TECHNICIAN_POOL[branch]

        n_open = t['open_wips']
        open_vals = _split_exact(rng, t['open_wip_value'], n_open)
        for i, v in enumerate(open_vals):
            age_days = 0 if i < today_n else rng.randint(1, 9)
            make, model = rng.choice(VEHICLE_MAKES_MODELS)
            records.append({
                "id": seq,
                "ro_number": f"RO-{seq:06d}", "client_name": f"Client #{seq:04d}",
                "vehicle_details": f"{make} {model}",
                "status": rng.choice(["Awaiting Parts", "In Progress", "Awaiting Authorisation"]),
                "service_advisor": rng.choice(advisors), "technician": rng.choice(techs),
                "estimated_value": round(v, 2), "notes": "",
                "parts_status": None, "parts_notes": None,
                "location_id": loc, "department_id": "SERVICE", "brand_id": "BMW",
                "created_at": (now - timedelta(days=age_days)).isoformat(),
            })
            seq += 1

        n_closed = max(1, round(t['locked_units'] * 1.5))
        closed_vals = _split_exact(rng, t['service_closed'], n_closed)
        for v in closed_vals:
            make, model = rng.choice(VEHICLE_MAKES_MODELS)
            records.append({
                "id": seq,
                "ro_number": f"RO-{seq:06d}", "client_name": f"Client #{seq:04d}",
                "vehicle_details": f"{make} {model}",
                "status": "Invoiced / Closed",
                "service_advisor": rng.choice(advisors), "technician": rng.choice(techs),
                "estimated_value": round(v, 2), "notes": "",
                "parts_status": None, "parts_notes": None,
                "location_id": loc, "department_id": "SERVICE", "brand_id": "BMW",
                "created_at": (now - timedelta(days=rng.randint(1, 28))).isoformat(),
            })
            seq += 1

    return records


def get_demo_vehicle_sales():
    """Session-cached accessor for get_demo_vehicle_sales_records()."""
    return _cached('demo_vehicle_sales', get_demo_vehicle_sales_records)


def get_demo_stockbook():
    """Session-cached accessor for get_demo_stockbook_records()."""
    return _cached('demo_stockbook', get_demo_stockbook_records)


def get_demo_wip():
    """Session-cached accessor for get_demo_wip_records()."""
    return _cached('demo_wip', get_demo_wip_records)


def init_presentation_session_state():
    """Populate st.session_state with the granular demo datasets as soon as
    Presentation Mode is active, so every page -- Command Center down to
    Stockroom/WIP drill-downs -- reads the exact same rows for the rest of
    the session."""
    get_demo_vehicle_sales()
    get_demo_stockbook()
    get_demo_wip()


# ------------------------------------------------------------------
# Aggregate projections (unchanged call signatures) -- now derived from the
# granular records above instead of independently generated, so headline
# tiles and departmental drill-downs are mathematically guaranteed to agree.
# ------------------------------------------------------------------

def get_demo_stock_rows():
    """Synthetic used_car_stock rows: 5 ageing buckets x 6 branches, 884 units total."""
    return [
        {
            "location_id": r["location_id"],
            "total_value": r["total_value"],
            "days_in_stock": r["days_in_stock"],
            "floorplan_status": r["floorplan_status"],
        }
        for r in get_demo_stockbook()
    ]


def get_demo_deal_desk_rows():
    """Synthetic deal_desk rows -- one per locked unit, summing to vehicle_retail/vaps/profit targets."""
    return [
        {
            "location_id": r["location_id"],
            "retail_price": r["retail_price"],
            "fi_vaps_revenue": r["fi_vaps_revenue"],
            "net_retained_profit": r["net_retained_profit"],
        }
        for r in get_demo_vehicle_sales()
    ]


def get_demo_parts_otc_rows():
    """Synthetic parts_otc rows, summing to parts_retail / its 30% margin per branch."""
    rng = _rng()
    rows = []
    for branch in DEALER_BRANCHES:
        t = BRANCH_TARGETS[branch]
        n = max(1, round(t['locked_units'] * 1.2))
        retail_vals = _split_exact(rng, t['parts_retail'], n)
        profit_vals = _split_exact(rng, t['parts_retail'] * OTC_MARGIN, n)
        for retail, profit in zip(retail_vals, profit_vals):
            rows.append({
                "location_id": LOCATION_IDS[branch],
                "retail_price": round(retail, 2),
                "net_profit": round(profit, 2),
            })
    return rows


def get_demo_doc_expenses_rows():
    """One synthetic doc_expenses row per branch, equal to its DOC target."""
    return [
        {"location_id": LOCATION_IDS[branch], "amount": round(BRANCH_TARGETS[branch]['doc'], 2)}
        for branch in DEALER_BRANCHES
    ]


def get_demo_service_wip_rows():
    """
    Synthetic service_wip rows: open WIPs (count/value from BRANCH_TARGETS,
    with exactly ROS_OPENED_TODAY_TOTAL of them dated today) plus closed/
    invoiced rows summing to each branch's service_closed target.
    """
    return [
        {
            "location_id": r["location_id"],
            "estimated_value": r["estimated_value"],
            "status": r["status"],
            "created_at": r["created_at"],
        }
        for r in get_demo_wip()
    ]
