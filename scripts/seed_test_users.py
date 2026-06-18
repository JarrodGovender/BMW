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
    ("SALES", "SALES_MANAGER"),
    ("ADMIN", "FINANCE_ADMIN"),
    ("HR", "HR_ADMIN"),
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

    df = pd.DataFrame(roster_rows)
    out_path = "test_accounts_matrix.xlsx"
    df.to_excel(out_path, index=False, engine="xlsxwriter")
    print(f"\nDone. {len(roster_rows)} accounts processed.")
    print(f"Roster (with plain-text passwords) written to: {out_path}")


if __name__ == "__main__":
    main()
