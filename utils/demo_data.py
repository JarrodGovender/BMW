"""
Presentation/Demo data layer for the Command Center.

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


def get_demo_stock_rows():
    """Synthetic used_car_stock rows: 5 ageing buckets x 6 branches, 884 units total."""
    rng = _rng()
    rows = []
    stock_weights = [BRANCH_TARGETS[b]['stock_value'] for b in DEALER_BRANCHES]

    for bucket, total_units in STOCK_AGEING_BUCKETS.items():
        per_branch_units = _split_int_exact(rng, total_units, stock_weights)
        lo, hi = BUCKET_DAY_RANGES[bucket]
        for branch, n_units in zip(DEALER_BRANCHES, per_branch_units):
            if n_units == 0:
                continue
            t = BRANCH_TARGETS[branch]
            bucket_value = t['stock_value'] * (total_units / sum(STOCK_AGEING_BUCKETS.values()))
            values = _split_exact(rng, bucket_value, n_units)
            for v in values:
                unencumbered = rng.random() < t['unencumbered_ratio']
                rows.append({
                    "location_id": LOCATION_IDS[branch],
                    "total_value": round(v, 2),
                    "days_in_stock": rng.randint(lo, hi),
                    "floorplan_status": "UNENCUMBERED" if unencumbered else "FLOORPLANNED",
                })
    return rows


def get_demo_deal_desk_rows():
    """Synthetic deal_desk rows -- one per locked unit, summing to vehicle_retail/vaps/profit targets."""
    rng = _rng()
    rows = []
    for branch in DEALER_BRANCHES:
        t = BRANCH_TARGETS[branch]
        n = t['locked_units']
        retail_vals = _split_exact(rng, t['vehicle_retail'], n)
        vaps_vals = _split_exact(rng, t['vaps'], n)
        profit_vals = _split_exact(rng, t['vehicle_retail'] * t['vehicle_margin'], n)
        for retail, vaps, profit in zip(retail_vals, vaps_vals, profit_vals):
            rows.append({
                "location_id": LOCATION_IDS[branch],
                "retail_price": round(retail, 2),
                "fi_vaps_revenue": round(vaps, 2),
                "net_retained_profit": round(profit, 2),
            })
    return rows


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
    rng = _rng()
    rows = []
    now = datetime.now()
    today_counts = _split_int_exact(
        rng, ROS_OPENED_TODAY_TOTAL, [BRANCH_TARGETS[b]['open_wips'] for b in DEALER_BRANCHES]
    )

    for branch, today_n in zip(DEALER_BRANCHES, today_counts):
        t = BRANCH_TARGETS[branch]
        loc = LOCATION_IDS[branch]

        n_open = t['open_wips']
        open_vals = _split_exact(rng, t['open_wip_value'], n_open)
        for i, v in enumerate(open_vals):
            age_days = 0 if i < today_n else rng.randint(1, 9)
            rows.append({
                "location_id": loc,
                "estimated_value": round(v, 2),
                "status": rng.choice(["Awaiting Parts", "In Progress", "Awaiting Authorisation"]),
                "created_at": (now - timedelta(days=age_days)).isoformat(),
            })

        n_closed = max(1, round(t['locked_units'] * 1.5))
        closed_vals = _split_exact(rng, t['service_closed'], n_closed)
        for v in closed_vals:
            rows.append({
                "location_id": loc,
                "estimated_value": round(v, 2),
                "status": "Invoiced / Closed",
                "created_at": (now - timedelta(days=rng.randint(1, 28))).isoformat(),
            })

    return rows
