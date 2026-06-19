"""
Dummy lead seeder for the Phase VI CRM Cadence Engine (public.crm_leads).

Run scripts/03_schema_fixes_and_crm.sql in the Supabase SQL Editor FIRST --
this script inserts rows via the Supabase REST/Python client, which can only
do DML (insert/select/update), not DDL. If crm_leads doesn't exist yet, every
insert below will fail with PGRST205.

--------------------------------------------------------------------------
ROLE NOTE
--------------------------------------------------------------------------
This script fetches active "SALES_EXEC"-equivalent users to assign leads to.
That literal role id does not exist anywhere in this codebase's role
vocabulary (config.py's roles fallback list, scripts/seed_test_users.py, and
views/shared_utils.py all agree on SALES_REP for individual sales staff and
SALES_MANAGER for the department head) -- so this script looks for
SALES_REP first, and falls back to SALES_MANAGER if no SALES_REP accounts
exist yet (which is the common case on a freshly seeded database, since
scripts/seed_test_users.py only creates one SALES_MANAGER per branch and no
SALES_REP rows at all). If neither role has any active users, leads are
still created with assigned_exec left NULL ("Unassigned") rather than
failing the whole batch.

--------------------------------------------------------------------------
HOW TO POINT THIS AT YOUR SUPABASE PROJECT
--------------------------------------------------------------------------
Same as scripts/seed_test_users.py -- either set SUPABASE_URL / SUPABASE_KEY
env vars, or run from the project root so .streamlit/secrets.toml is found.
--------------------------------------------------------------------------
"""

import os
import random
from datetime import datetime, timedelta
from supabase import create_client

# --- 1. CREDENTIALS ---------------------------------------------------
def load_supabase_credentials():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if url and key:
        return url, key

    try:
        import tomllib
        secrets_path = os.path.join(".streamlit", "secrets.toml")
        with open(secrets_path, "rb") as f:
            secrets = tomllib.load(f)
        return secrets["supabase"]["url"], secrets["supabase"]["key"]
    except Exception:
        raise RuntimeError(
            "Could not find Supabase credentials. Set SUPABASE_URL and "
            "SUPABASE_KEY environment variables, or run this script from "
            "the project root where .streamlit/secrets.toml exists."
        )

SUPABASE_URL, SUPABASE_KEY = load_supabase_credentials()
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. SEED DATA POOLS -------------------------------------------------
LOCATIONS = [
    "BMW_SANDTON", "BMW_BEDFORDVIEW", "BMW_EASTRAND",
    "BMW_DALPARK", "MF_SANDTON", "MF_FOURWAYS",
]

VEHICLES_BY_LOCATION = {
    "BMW_SANDTON": ["BMW X5 xDrive40i", "BMW 3 Series 320d", "BMW M4 Competition", "BMW iX xDrive50"],
    "BMW_BEDFORDVIEW": ["BMW X3 xDrive20d", "BMW 5 Series 520d", "BMW 1 Series 118i", "BMW X1 sDrive18i"],
    "BMW_EASTRAND": ["BMW X5 xDrive40i", "BMW 3 Series 318i", "MINI Cooper S", "BMW X3 xDrive20d"],
    "BMW_DALPARK": ["BMW 1 Series 116i", "BMW X1 sDrive18i", "BMW 3 Series 320i", "MINI Cooper"],
    "MF_SANDTON": ["MG ZS 1.5", "Honda CR-V 1.5T", "MG HS 1.5T", "Honda Ballade 1.5"],
    "MF_FOURWAYS": ["MG 3 1.5", "JAC T6 2.0D", "Honda Civic 1.5T", "MG ZS EV"],
}

# Rough ZAR retail price ranges per vehicle, used to seed a believable
# estimated_value per lead (low, high).
VEHICLE_VALUE_RANGES = {
    "BMW X5 xDrive40i": (1_450_000, 1_650_000), "BMW 3 Series 320d": (750_000, 850_000),
    "BMW M4 Competition": (1_950_000, 2_200_000), "BMW iX xDrive50": (1_850_000, 2_100_000),
    "BMW X3 xDrive20d": (950_000, 1_100_000), "BMW 5 Series 520d": (1_100_000, 1_300_000),
    "BMW 1 Series 118i": (550_000, 650_000), "BMW X1 sDrive18i": (650_000, 750_000),
    "BMW 3 Series 318i": (650_000, 750_000), "MINI Cooper S": (550_000, 650_000),
    "BMW 1 Series 116i": (500_000, 580_000), "BMW 3 Series 320i": (700_000, 800_000),
    "MINI Cooper": (480_000, 560_000), "MG ZS 1.5": (320_000, 380_000),
    "Honda CR-V 1.5T": (550_000, 650_000), "MG HS 1.5T": (450_000, 520_000),
    "Honda Ballade 1.5": (320_000, 380_000), "MG 3 1.5": (260_000, 310_000),
    "JAC T6 2.0D": (480_000, 560_000), "Honda Civic 1.5T": (520_000, 600_000),
    "MG ZS EV": (650_000, 720_000),
}

CUSTOMER_NAMES = [
    "Thabo Mokoena", "Sarah Jenkins", "Pieter van der Merwe", "Naledi Khumalo",
    "James Patterson", "Fatima Patel", "Sipho Dlamini", "Emma Roberts",
    "Johan Botha", "Lindiwe Zulu", "Michael Chen", "Aisha Mahmood",
    "Werner Steyn", "Precious Ndlovu", "David O'Connor", "Zanele Mbeki",
    "Andries Kruger", "Priya Naidoo", "Kevin Smith", "Bongani Sithole",
    "Chantelle du Toit", "Riaan Pretorius", "Nomvula Mahlangu", "Stephen Lee",
    "Karabo Maluleke",
]

SOURCES = ["Website Enquiry", "Walk-in", "AutoTrader", "Referral", "Showroom Floor", "Call-in Campaign"]
STATUSES = ["New", "Contacted", "Test Drive", "Negotiation", "Closed"]
TEMPERATURES = ["Cold", "Warm", "Hot"]


def fetch_active_execs():
    """Return list of (username, location_id) for active sales staff, preferring SALES_REP."""
    for role in ("SALES_REP", "SALES_MANAGER"):
        try:
            res = (
                supabase.table("users")
                .select("username, location_id, is_active")
                .eq("role_id", role)
                .eq("is_active", True)
                .execute()
                .data
            )
        except Exception as e:
            print(f"[WARN] Could not query users for role={role}: {e}")
            res = []
        if res:
            print(f"[INFO] Found {len(res)} active {role} user(s) to assign leads to.")
            return [(r["username"], r.get("location_id")) for r in res]
    print("[WARN] No active SALES_REP or SALES_MANAGER users found -- leads will be seeded as Unassigned.")
    return []


def main():
    execs = fetch_active_execs()
    now = datetime.utcnow()

    leads = []
    for i in range(25):
        location_id = random.choice(LOCATIONS)
        vehicle = random.choice(VEHICLES_BY_LOCATION[location_id])
        status = random.choices(STATUSES, weights=[30, 25, 20, 15, 10])[0]
        temperature = random.choices(TEMPERATURES, weights=[25, 40, 35])[0]

        same_branch_execs = [u for u, loc in execs if loc == location_id]
        assignee_pool = same_branch_execs if same_branch_execs else [u for u, _ in execs]
        assigned_exec = random.choice(assignee_pool) if assignee_pool else None

        last_contact = now - timedelta(days=random.randint(0, 14), hours=random.randint(0, 23))
        next_action_due = now + timedelta(hours=random.randint(-48, 96))
        low, high = VEHICLE_VALUE_RANGES.get(vehicle, (300_000, 500_000))
        estimated_value = round(random.uniform(low, high), 2)

        leads.append({
            "customer_name": CUSTOMER_NAMES[i],
            "contact_number": f"08{random.randint(10000000, 99999999)}",
            "vehicle_of_interest": vehicle,
            "source": random.choice(SOURCES),
            "status": status,
            "temperature": temperature,
            "last_contact": last_contact.isoformat(),
            "next_action_due": next_action_due.isoformat(),
            "estimated_value": estimated_value,
            "assigned_exec": assigned_exec,
            "location_id": location_id,
            "department_id": "NEW_SALES",
            "brand_id": "ALL_BRANDS",
        })

    try:
        supabase.table("crm_leads").insert(leads).execute()
        print(f"[DONE] Inserted {len(leads)} dummy leads into crm_leads.")
    except Exception as e:
        print(f"[FAILED] Could not insert leads: {e}")
        print("[HINT] Did you run scripts/03_schema_fixes_and_crm.sql in the Supabase SQL Editor first?")


if __name__ == "__main__":
    main()
