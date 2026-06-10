import requests
import random
from datetime import datetime
from supabase import create_client, Client

# ==========================================
# 1. YOUR SECURE CREDENTIALS
# ==========================================
APOLLO_API_KEY = "3UHsfp2j7fgkoKU4WST8tg"
SUPABASE_URL = "https://ofvsqtdoezesycsstkkh.supabase.co"
SUPABASE_KEY = "sb_secret_kUj0BWaKzfiDSfDQS-1nQg_Bh1brErP"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 2. THE APOLLO.IO ENRICHMENT ENGINE
# ==========================================
def hunt_for_fleet_leads():
    print("🚀 Initiating Apollo.io B2B Fleet Hunt...")
    
    url = "https://api.apollo.io/api/v1/mixed_people/search"
    
    headers = {
        "Cache-Control": "no-cache",
        "Content-Type": "application/json"
    }
    
    # We are explicitly hunting for decision makers in Gauteng
    payload = {
        "api_key": APOLLO_API_KEY,
        "person_titles": ["Fleet Manager", "Procurement Director", "Operations Head", "Chief Executive Officer"],
        "person_locations": ["Sandton, South Africa", "Johannesburg, South Africa", "Midrand, South Africa"],
        "organization_num_employees_ranges": ["50,1000", "1000,10000"],
        "per_page": 5 # Limit to 5 high-quality leads per day
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        people = data.get('people', [])
        
        extracted_leads = []
        for person in people:
            org = person.get('organization', {})
            
            # Smart Scoring Logic
            title = str(person.get('title', '')).lower()
            base_score = random.randint(70, 85)
            if 'fleet' in title or 'procurement' in title:
                base_score += 10 # Bump score for direct vehicle decision makers
                
            lead_data = {
                "company": org.get('name', 'Unknown Enterprise'),
                "location": person.get('city', 'Johannesburg'),
                "target": person.get('title', 'Executive'),
                "score": min(base_score, 99),
                "lead_date": datetime.now().strftime('%Y-%m-%d'),
                "signal": f"Automated Extraction: {org.get('name')} fits target employee size for fleet expansion.",
                "status": "Unassigned",
                "public_email": person.get('email', 'N/A'),
                "public_phone": person.get('work_phone', 'N/A') if person.get('work_phone') else org.get('primary_phone', 'N/A'),
                "company_website": org.get('website_url', 'N/A'),
                "linkedin_url": person.get('linkedin_url', 'N/A')
            }
            extracted_leads.append(lead_data)
            print(f"🎯 Acquired: {lead_data['target']} at {lead_data['company']}")
            
        return extracted_leads
    else:
        print(f"❌ Apollo API Error: {response.text}")
        return []

# ==========================================
# 3. THE SUPABASE INJECTION PROTOCOL
# ==========================================
if __name__ == "__main__":
    new_leads = hunt_for_fleet_leads()
    
    if new_leads:
        try:
            # Push the data seamlessly into your live database
            result = supabase.table("leads").insert(new_leads).execute()
            print(f"✅ Successfully injected {len(new_leads)} new B2B leads into the Hub!")
        except Exception as e:
            print(f"❌ Database Injection Failed: {str(e)}")
    else:
        print("ℹ️ No new leads found matching criteria today.")
