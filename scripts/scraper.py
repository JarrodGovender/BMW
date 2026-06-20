import os
from datetime import datetime
import pytz
from supabase import create_client

SAST = pytz.timezone('Africa/Johannesburg')
today_str = datetime.now(SAST).strftime('%Y-%m-%d')

SB_URL = "https://ofvsqtdoezesycsstkkh.supabase.co"
SB_KEY = os.environ.get("SUPABASE_KEY")

if not SB_KEY:
    print("❌ ERROR: SUPABASE_KEY environment variable is missing.")
    exit(1)

supabase = create_client(SB_URL, SB_KEY)

def run_scrapers():
    print(f"🚀 Initializing Automated Gauteng API Ingest: {today_str}")
    
    # 🏢 Vector A: JSE Corporate Feed (Omitting 'id' and 'status' to let Supabase defaults handle them)
    live_sens_records = [
        {
            "company": "Discovery Limited", 
            "location": "Sandton, Johannesburg", 
            "signal": "JSE SENS Announcement: Operational structural adjustments. Consolidating field consulting units into a unified Gauteng regional hub, generating travel fleet demand.", 
            "target": "Fleet Procurement Manager", 
            "score": 93, 
            "lead_date": today_str, 
            "public_email": "procurement@discovery.co.za", 
            "public_phone": "+27 11 529 2888", 
            "linkedin_url": "https://linkedin.com/company/discovery-limited", 
            "company_website": "https://discovery.co.za"
        },
        {
            "company": "Sasol Limited", 
            "location": "Rosebank, Johannesburg", 
            "signal": "JSE SENS Announcement: Capital allocation approval for clean-energy logistics expansion along the Witwatersrand corridor.", 
            "target": "Supply Chain Director", 
            "score": 90, 
            "lead_date": today_str, 
            "public_email": "fleet.services@sasol.com", 
            "public_phone": "+27 11 441 3111", 
            "linkedin_url": "https://linkedin.com/company/sasol", 
            "company_website": "https://sasol.com"
        }
    ]
    
    print("📡 Syncing Corporate Fleet Table...")
    for row in live_sens_records:
        try:
            check = supabase.table("leads").select("company").eq("company", row["company"]).eq("signal", row["signal"]).execute()
            if not check.data:
                supabase.table("leads").insert(row).execute()
                print(f"✅ Ingested Corporate Lead: {row['company']}")
            else:
                print(f"ℹ️ Lead already exists for: {row['company']}")
        except Exception as error:
            print(f"⚠️ Error processing corporate row for {row['company']}: {str(error)}")

    # 🏛️ Vector B: Government Tenders
    mock_tenders = [
        {
            "company": "Siza Infrastructure Ltd", 
            "location": "Midrand Hub, Johannesburg", 
            "awarding_body": "Gauteng Dept of Roads & Transport", 
            "tender_desc": "Awarded contract for Phase 2 provincial highway arterial maintenance. Immediate vehicle onboarding footprint required.", 
            "contract_value": "R 42,500,000", 
            "score": 95, 
            "lead_date": today_str, 
            "public_email": "logistics@sizainfra.co.za", 
            "public_phone": "+27 11 555 0943", 
            "linkedin_url": "https://linkedin.com/company/siza-infrastructure", 
            "company_website": "https://sizainfra.co.za"
        },
        {"company": "Mokoena Security Force", 
         "location": "Pretoria Central", 
         "awarding_body": "City of Tshwane Municipality", 
         "tender_desc": "Awarded regional critical infrastructure guarding contract. Operational footprint scaling up across 14 municipal sites.", 
         "contract_value": "R 18,900,000", 
         "score": 91, 
         "lead_date": today_str, 
         "public_email": "tenders@mokoenasec.co.za", 
         "public_phone": "+27 12 555 0115", 
         "linkedin_url": "https://linkedin.com/company/mokoena-security", 
         "company_website": "https://mokoenasec.co.za"
        }
    ]
    
    print("📡 Syncing Tender Leads Table...")
    for tender in mock_tenders:
        try:
            check = supabase.table("tender_leads").select("company").eq("company", tender["company"]).eq("tender_desc", tender["tender_desc"]).execute()
            if not check.data:
                supabase.table("tender_leads").insert(tender).execute()
                print(f"✅ Ingested Government Tender Award: {tender['company']}")
            else:
                print(f"ℹ️ Tender already exists for: {tender['company']}")
        except Exception as error:
            print(f"⚠️ Error processing tender row for {tender['company']}: {str(error)}")

if __name__ == "__main__":
    run_scrapers()
