"""
Standalone test-account seeder for the Phase V Enterprise 4D Matrix.

Creates one test user per (location x department) combination so you can
manually verify location/department/role/brand scoping across every branch.
This script does NOT touch any Streamlit app file — it only talks to Supabase
directly and writes an Excel roster.

--------------------------------------------------------------------------
HOW TO POINT THIS AT YOUR SUPABASE PROJECT
--------------------------------------------------------------------------
Option A (recommended) — environment variables:
    PowerShell:
        $env:SUPABASE_URL = "https://xxxx.supabase.co"
        $env:SUPABASE_KEY = "your-service-or-anon-key"
        python scripts/seed_test_users.py

Option B — reuse your existing .streamlit/secrets.toml:
    This script will automatically fall back to reading
    SUPABASE_URL/SUPABASE_KEY from .streamlit/secrets.toml's [supabase]
    section (the same file the Streamlit app already uses) if the
    environment variables above are not set.

--------------------------------------------------------------------------
ROLE NOTE
--------------------------------------------------------------------------
The SERVICE department is assigned WORKSHOP_MANAGER rather than
SERVICE_MANAGER. WORKSHOP_MANAGER is the role the app's matrix filters and
routing logic actually recognize (see apply_matrix_filters() and the
Route A dispatch condition) — SERVICE_MANAGER does not exist anywhere in
the codebase's role vocabulary, so using it would silently fall through
to a stricter, brand-scoped filter bucket instead of the intended
manager-tier bypass.

SALES and ADMIN are likewise mapped to the actual department_id rows that
exist in this Supabase project's `departments` table (NEW_SALES and
FINANCE respectively) — a generic "SALES" or "ADMIN" id does not exist
and is rejected by the users_department_id_fkey constraint.

--------------------------------------------------------------------------
SCHEMA PREREQUISITE — HR
--------------------------------------------------------------------------
This database had no "HR" row in `departments` and no "HR_ADMIN" row in
`roles` until this script was first run — meaning the HR module
(views/route_c_hr.py) was unreachable by any real account. Both rows were
added once, by hand:
    departments: {"id": "HR", "name": "Human Resources"}
    roles:       {"id": "HR_ADMIN", "title": "HR Administrator", "access_level": 2}
If you point this script at a different Supabase project, add those two
rows first or the HR test-account insert will fail the same way.

--------------------------------------------------------------------------
ENTERPRISE ACCOUNTS — DIRECTOR / PROPERTY_MANAGER
--------------------------------------------------------------------------
These two roles aren't branch-scoped, so they don't fit the location x
department loop above. Rather than NULL location/department/brand (which
buys nothing — these columns aren't NOT NULL, but apply_matrix_filters()
still runs an .eq() against whatever value is stored, and an .eq() on
NULL matches nothing), they're pinned to this project's existing global
sentinel rows: locations.GLOBAL_HQ, departments.ALL_DEPTS, brands.ALL_BRANDS.

Caveat: apply_matrix_filters() only gives DIRECTOR a true bypass (no
filter at all). PROPERTY_MANAGER falls in the location-only bucket
(query.eq("location_id", loc)) — so test_property will only ever see
rows tagged location_id == "GLOBAL_HQ", and no branch-level data (stock,
WIP, deals, etc.) carries that tag today. test_director will see
everything, unaffected by this, since DIRECTOR skips filtering entirely.
This is a property of apply_matrix_filters() itself, not something this
script can fix — flagging it so a "PROPERTY_MANAGER sees no data" result
isn't mistaken for a seeding bug.
--------------------------------------------------------------------------
"""

import os
import hashlib
import pandas as pd
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

# --- 2. SEED DATA RULES -------------------------------------------------
LOCATIONS = [
    ("BMW_SANDTON", "BMW Sandton"),
    ("BMW_BEDFORDVIEW", "BMW Bedfordview"),
    ("BMW_EASTRAND", "BMW East Rand"),
    ("BMW_DALPARK", "BMW Dalpark"),
    ("MF_SANDTON", "MF Sandton"),
    ("MF_FOURWAYS", "MF Fourways"),
]

DEPARTMENTS = [
    ("SERVICE", "WORKSHOP_MANAGER"),
    ("PARTS", "PARTS_MANAGER"),
    ("NEW_SALES", "SALES_MANAGER"),
    ("FINANCE", "FINANCE_ADMIN"),
    ("HR", "HR_ADMIN"),
]

ENTERPRISE_ACCOUNTS = [
    {
        "username": "test_director",
        "name": "Test Director — Enterprise",
        "role": "DIRECTOR",
        "location_id": "GLOBAL_HQ",
        "department_id": "ALL_DEPTS",
        "brand_id": "ALL_BRANDS",
    },
    {
        "username": "test_property",
        "name": "Test Property Manager — Enterprise",
        "role": "PROPERTY_MANAGER",
        "location_id": "GLOBAL_HQ",
        "department_id": "ALL_DEPTS",
        "brand_id": "ALL_BRANDS",
    },
]

PLAIN_PASSWORD = "Test123!"
HASHED_PASSWORD = hashlib.sha256(PLAIN_PASSWORD.encode()).hexdigest()


def get_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()


# --- 3. GENERATE + INSERT -------------------------------------------------
def main():
    roster_rows = []

    for loc_id, loc_label in LOCATIONS:
        for dept_id, role in DEPARTMENTS:
            username = f"test_{loc_id.lower()}_{dept_id.lower()}"
            name = f"Test {dept_id.title()} — {loc_label}"

            payload = {
                "username": username,
                "name": name,
                "password": HASHED_PASSWORD,
                "role": role,
                "role_id": role,
                "location_id": loc_id,
                "department_id": dept_id,
                "brand_id": "ALL_BRANDS",
                "is_active": True,
            }

            status = "CREATED"
            try:
                supabase.table("users").insert(payload).execute()
            except Exception as e:
                status = f"FAILED: {e}"

            roster_rows.append({
                "USERNAME": username,
                "PASSWORD": PLAIN_PASSWORD,
                "LOCATION": loc_label,
                "LOCATION_ID": loc_id,
                "DEPARTMENT": dept_id,
                "ROLE": role,
                "STATUS": status,
            })
            print(f"[{status}] {username} -> {loc_id} / {dept_id} / {role}")

    for acct in ENTERPRISE_ACCOUNTS:
        payload = {
            "username": acct["username"],
            "name": acct["name"],
            "password": HASHED_PASSWORD,
            "role": acct["role"],
            "role_id": acct["role"],
            "location_id": acct["location_id"],
            "department_id": acct["department_id"],
            "brand_id": acct["brand_id"],
            "is_active": True,
        }

        status = "CREATED"
        try:
            supabase.table("users").insert(payload).execute()
        except Exception as e:
            status = f"FAILED: {e}"

        roster_rows.append({
            "USERNAME": acct["username"],
            "PASSWORD": PLAIN_PASSWORD,
            "LOCATION": "Enterprise (Global)",
            "LOCATION_ID": acct["location_id"],
            "DEPARTMENT": acct["department_id"],
            "ROLE": acct["role"],
            "STATUS": status,
        })
        print(f"[{status}] {acct['username']} -> {acct['location_id']} / {acct['department_id']} / {acct['role']}")

    df = pd.DataFrame(roster_rows)
    out_path = "test_accounts_matrix.xlsx"
    df.to_excel(out_path, index=False, engine="xlsxwriter")
    print(f"\nDone. {len(roster_rows)} accounts processed.")
    print(f"Roster (with plain-text passwords) written to: {out_path}")


if __name__ == "__main__":
    main()
