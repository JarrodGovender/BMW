import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
import io
from supabase import create_client, Client

# ==========================================
# 1. INITIALIZATION & PRODUCTION API SETUP
# ==========================================
st.set_page_config(page_title="BMW Sandton Lead Hub", layout="wide")
SAST = pytz.timezone('Africa/Johannesburg')

BMW_LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/4/44/BMW.svg"
M_SPORT_LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/b/b3/BMW_M_logo.svg"

def safe_rerun():
    """Waterproof context manager to handle page refreshes across all Streamlit versions."""
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

# ====================================================================
# OFFICIAL BMW DIGITAL DESIGN IDENTITY CSS INJECTION
# ====================================================================
st.markdown("""
    <style>
        html, body, [data-testid="stAppViewContainer"] {
            font-family: "BMWTypeNext", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
            background-color: #FFFFFF !important;
        }
        
        .stTextInput>div>div>input, .stSelectbox>div>div>div, .stTextArea>div>div>textarea {
            border: 1px solid #E5E5E5 !important;
            border-radius: 0px !important; 
            background-color: #F6F6F6 !important;
            color: #262626 !important;
            font-size: 0.95rem !important;
        }
        
        div.stButton {
            width: auto !important;
            max-width: 240px !important; 
            display: inline-block !important;
            margin-top: 0.5rem !important;
        }
        
        div.stButton > button, 
        div.stButton > button:first-child {
            background-color: #000000 !important; 
            border-radius: 0px !important;         
            border: 1px solid #000000 !important;
            padding: 0.6rem 0rem !important;       
            font-weight: 500 !important;
            font-size: 0.8rem !important;
            letter-spacing: 1.5px !important;     
            text-transform: uppercase !important;  
            width: 240px !important;               
            max-width: 240px !important;
            height: 42px !important;
            display: block !important;
            transition: all 0.2s ease-in-out !important;
        }
        
        div.stButton > button * {
            color: #FFFFFF !important;
            width: auto !important;
            max-width: none !important;
            display: inline-block !important;
        }
        
        div.stButton > button:hover {
            background-color: #262626 !important;
        }
        
        [data-testid="stMetricValue"] {
            font-size: 2.3rem !important;
            font-weight: 300 !important; 
            color: #000000 !important;
            letter-spacing: -1px !important;
        }
        
        button[data-baseweb="tab"] {
            font-size: 0.9rem !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
        }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_supabase_client() -> Client:
    sb_url = st.secrets["supabase"]["url"]
    sb_key = st.secrets["supabase"]["key"]
    return create_client(sb_url, sb_key)

try:
    supabase = get_supabase_client()
except Exception as e:
    st.error(f"🔒 Secure API Hook Connection Error: {str(e)}")
    st.stop()

# Operational Time Guard Lockout
now_sast = datetime.now(SAST)
if now_sast.hour >= 22 or now_sast.hour < 6:
    st.error("🛑 **Access Denied: System Offline.**")
    st.stop()

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
    st.session_state['user'] = None
    st.session_state['name'] = None
    st.session_state['role'] = None

if st.session_state['authenticated']:
    # Header Section
    st.markdown(f"""
        <div style='display: flex; align-items: center; gap: 18px;'>
            <img src='{BMW_LOGO_URL}' width='50'>
            <img src='{M_SPORT_LOGO_URL}' width='65' style='margin-top: 4px;'>
            <div>
                <h3 style='margin: 0; font-weight: 400;'>BMW SANDTON</h3>
                <p style='margin: 0; font-size: 0.75rem; color: #666666; letter-spacing: 1px;'>EXECUTIVE DATA AND HUB MANAGEMENT</p>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"LOGGED IN AS: **{st.session_state['name'].upper()}** ({st.session_state['role'].replace('_', ' ').upper()})")
    st.markdown("---")

    MANAGEMENT_ROLES = ['dealer_principal', 'finance_admin', 'sales_manager']
    
    # 🌟 CORE FIX: All authenticated users can access the Used Car Stock Module tab
    if st.session_state['role'] in MANAGEMENT_ROLES:
        tab1, tab2, tab3, tab4 = st.tabs(["🔥 AVAILABLE DAILY FEED", "💼 MY CLAIMED ACCOUNTS", "🚗 USED CAR STOCK STOCKROOM", "📊 COMMAND OVERVIEW"])
    else:
        tab1, tab2, tab3 = st.tabs(["🔥 AVAILABLE DAILY FEED", "💼 MY CLAIMED ACCOUNTS", "🚗 USED CAR STOCK STOCKROOM"])

    # ---- TAB 1 & 2: LEADS FEEDS GENERATOR ----
    with tab1:
        st.info("Daily opportunity network channels active.")
    with tab2:
        st.caption("Profile specific claims registry matrix.")

    # ---- 🚗 TAB 3: UNIVERSAL USED CAR STOCKROOM NODE ----
    with tab3:
        st.markdown("### 🚗 LIVE USED CAR STOCKROOM")
        st.caption("Single source of truth inventory registry synchronized with Supabase.")
        
        # 🔒 ADMIN ONLY CONTROLS: Exclusively visible to Finance/Admin profiles
        if st.session_state['role'] == 'finance_admin':
            with st.expander("🛠️ ADMIN CONSOLE: BULK STOCK LEDGER DATA PASTE TERMINAL", expanded=False):
                st.markdown("#### Paste Spreadsheet Data Rows")
                st.caption("Open your stock workbook sheet, highlight data rows from VSB No down to Location, copy them, and paste them straight into the input terminal field below:")
                
                raw_paste_data = st.text_area("PASTE RAW ROWS HERE (Supports Tab/CSV Delimited fields)", height=250, placeholder="109237\tX4 xDrive20d Sport\t30/01/2026\t126\t928605.99\tLHP")
                
                if st.button("PROCESS AND OVERWRITE INVENTORY", key="process_stock_paste_btn"):
                    if raw_paste_data.strip():
                        try:
                            # Parse lines smoothly regardless of platform format markers
                            lines = raw_paste_data.strip().split('\n')
                            records_processed = 0
                            
                            # Clear old stock data cleanly to populate fresh morning registers
                            supabase.table("used_car_stock").delete().neq("vsb_no", "placeholder_wiped").execute()
                            
                            for line in lines:
                                parts = line.split('\t') if '\t' in line else line.split(',')
                                if len(parts) >= 2 and parts[0].strip().isdigit():
                                    vsb = parts[0].strip()
                                    desc = parts[1].strip()
                                    into_stk = parts[2].strip() if len(parts) > 2 else ''
                                    
                                    try:
                                        days = int(float(parts[3].strip())) if len(parts) > 3 and parts[3].strip() else 0
                                    except:
                                        days = 0
                                        
                                    try:
                                        val = float(parts[4].strip().replace('R', '').replace(' ', '').replace(',', '')) if len(parts) > 4 and parts[4].strip() else 0.00
                                    except:
                                        val = 0.00
                                        
                                    loc = parts[5].strip() if len(parts) > 5 else 'Sandton'
                                    
                                    supabase.table("used_car_stock").insert({
                                        "vsb_no": vsb, "description": desc, "into_stock": into_stk,
                                        "days_in_stock": days, "total_value": val, "location": loc
                                    }).execute()
                                    records_processed += 1
                                    
                            st.success(f"🎉 Inventory refreshed successfully. {records_processed} used vehicle entities committed to cloud storage.")
                            safe_rerun()
                        except Exception as parse_ex:
                            st.error(f"Data mapping mismatch: {str(parse_ex)}")
                    else:
                        st.warning("Please populate the data terminal with text matrix lines before submitting.")

        # ---- DYNAMIC CATALOG MONITORING FOR ALL USER ROLES ----
        try:
            stock_res = supabase.table("used_car_stock").select("*").order("days_in_stock", desc=True).execute()
            df_live_stock = pd.DataFrame(stock_res.data) if stock_res.data else pd.DataFrame()
        except:
            df_live_stock = pd.DataFrame()

        if not df_live_stock.empty:
            # Calculate metrics dynamically on the fly safely from database lines
            cnt_units = len(df_live_stock)
            sum_capital = df_live_stock['total_value'].sum()
            avg_age = df_live_stock['days_in_stock'].mean()
            
            s_col1, s_col2, s_col3 = st.columns(3)
            s_col1.metric("USED VEHICLES AVAILABLE", f"{cnt_units} UNITS")
            s_col2.metric("STOCKHOLDING CAPITAL VALUE", f"R {sum_capital:,.2f}")
            s_col3.metric("AVERAGE AGE IN STOCK", f"{int(avg_age)} DAYS")
            
            st.markdown("---")
            search_query = st.text_input("🔍 LIVE SEARCH INVENTORY CATALOG (Type Model Name or VSB No)", "").strip().lower()
            
            # Apply instant filter mappings onto current interface frame
            if search_query:
                filtered_stock = df_live_stock[
                    df_live_stock['description'].astype(str).str.lower().str.contains(search_query) |
                    df_live_stock['vsb_no'].astype(str).str.lower().str.contains(search_query)
                ].copy()
            else:
                filtered_stock = df_live_stock.copy()
                
            filtered_stock.columns = ["VSB NUMBER", "VEHICLE DESCRIPTION", "INTO STOCK DATE", "DAYS ON FLOOR", "CAPITAL VAL (ZAR)", "SHOWROOM SITE", "TIMESTAMP LINK"]
            
            # Format numbers safely as readable string matrices for standard table display
            filtered_stock["CAPITAL VAL (ZAR)"] = filtered_stock["CAPITAL VAL (ZAR)"].map(lambda x: f"R {float(x):,.2f}")
            st.table(filtered_stock[["VSB NUMBER", "VEHICLE DESCRIPTION", "INTO STOCK DATE", "DAYS ON FLOOR", "CAPITAL VAL (ZAR)", "SHOWROOM SITE"]])
        else:
            st.info("💡 The used vehicle stock register is currently empty. Waiting for Finance/Admin profile upload cycle sync.")

    # ---- TAB 4: COMMAND CONTROLS ----
    if st.session_state['role'] in MANAGEMENT_ROLES:
        with tab4:
            st.markdown("### 📊 AUDIT MONITOR NODE")

else:
    # Gateway Authentication Interface Layer
    gate_col1, gate_col2, gate_col3 = st.columns([1.5, 3, 1.5])
    with gate_col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(f"<div class='bmw-logo-centered-header'><img src='{BMW_LOGO_URL}' width='82'><img src='{M_SPORT_LOGO_URL}' width='98' style='margin-top:6px;'></div>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; font-weight: 300; margin-top:25px; margin-bottom: 0;'>BMW SANDTON</h2>", unsafe_allow_html=True)
        
        auth_tab, signup_tab = st.tabs(["🔒 SECURE SIGN IN", "📝 CREATE ACCESS ACCOUNT"])
        with auth_tab:
            l_user = st.text_input("USERNAME", key="login_user").strip().lower()
            l_pass = st.text_input("PASSWORD", type="password", key="login_pass")
            if st.button("AUTHENTICATE ACCESS", key="login_btn") and l_user and l_pass:
                try:
                    res = supabase.table("users").select("name", "role", "password").eq("username", l_user).execute()
                    if res.data:
                        import hashlib
                        if res.data[0]['password'] == hashlib.sha256(l_pass.encode()).hexdigest():
                            st.session_state['authenticated'] = True
                            st.session_state['user'] = l_user
                            st.session_state['name'] = res.data[0]['name']
                            st.session_state['role'] = res.data[0]['role']
                            safe_rerun()
                        else: st.error("Authentication rejected.")
                    else: st.error("Identity matching failed.")
                except Exception as e: st.error(f"Handshake Error: {str(e)}")
                
        with signup_tab:
            st.markdown("### INITIALIZE SYSTEM ACCOUNT")
            n_name = st.text_input("FULL NAME", key="reg_name").strip()
            n_user = st.text_input("CHOOSE USERNAME", key="reg_user").strip().lower()
            n_pass = st.text_input("CHOOSE PASSWORD", type="password", key="reg_pass")
            c_role = st.selectbox("SELECT POSITION", ["Sales Representative", "Dealer Principal", "Finance/Admin", "Sales Manager"], key="reg_role")
            s_code = st.text_input("DEALERSHIP SECURITY CODE", type="password", key="reg_code")
            
            if st.button("INITIALIZE PROFILE", key="signup_btn"):
                if n_name and n_user and n_pass and s_code == "SandtonBMW2026":
                    try:
                        role_map = {'Dealer Principal':'dealer_principal', 'Finance/Admin':'finance_admin', 'Sales Manager':'sales_manager', 'Sales Representative':'sales_rep'}
                        import hashlib
                        supabase.table("users").insert({
                            "username": n_user, "password": hashlib.sha256(n_pass.encode()).hexdigest(), "name": n_name, "role": role_map[c_role]
                        }).execute()
                        st.success("🎉 Profile initialized. Proceed to Sign In.")
                    except Exception as e: st.error(f"Error: {str(e)}")
                else: st.error("Verification parameters invalid.")
    st.stop()
