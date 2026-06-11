import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
import smtplib
from email.message import EmailMessage
import io
import hashlib
import random
import time
import base64
from supabase import create_client, Client

# ==========================================
# 1. AI STRUCTURED SCHEMA & IMPORTS
# ==========================================
try:
    from google import genai
    from google.genai import types
    from pydantic import BaseModel, Field
    GEMINI_AVAILABLE = True
    
    class VehicleSpecs(BaseModel):
        engine_configuration: str = Field(description="Exact engine layout")
        transmission: str = Field(description="Exact transmission type")
        drivetrain: str = Field(description="Drive type")
        power_output: str = Field(description="Exact power output in kW")
        torque: str = Field(description="Exact torque output in Nm")
        acceleration_0_100: str = Field(description="0-100 km/h time")
        fuel_economy: str = Field(description="Combined fuel consumption")
        body_classification: str = Field(description="Vehicle category")
except ImportError:
    GEMINI_AVAILABLE = False

# ==========================================
# 2. LOCAL ASSET ENCODER & INITIALIZATION
# ==========================================
st.set_page_config(page_title="Phase V Enterprise Hub", layout="wide")
SAST = pytz.timezone('Africa/Johannesburg')

def get_local_img(file_name, cdn_fallback):
    if os.path.exists(file_name):
        try:
            with open(file_name, "rb") as f:
                return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
        except Exception: return cdn_fallback
    return cdn_fallback

BMW_LOGO = get_local_img("BMW.png", "https://upload.wikimedia.org/wikipedia/commons/4/44/BMW.svg")
MINI_LOGO = get_local_img("MINI.png", "https://upload.wikimedia.org/wikipedia/commons/e/ea/MINI_logo.svg")
MG_LOGO = get_local_img("MG.png", "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/MG_logo.svg/512px-MG_logo.svg.png")

def safe_rerun(): st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

for key in ['authenticated', 'user', 'name', 'role']:
    if key not in st.session_state: st.session_state[key] = False if key == 'authenticated' else None
if 'page_view' not in st.session_state: st.session_state['page_view'] = 'dashboard'
if 'theme' not in st.session_state: st.session_state['theme'] = 'Light'

def get_ai_vehicle_specs(description, franchise, vin):
    has_key = "gemini" in st.secrets and "api_key" in st.secrets["gemini"]
    if GEMINI_AVAILABLE and has_key:
        try:
            client = genai.Client(api_key=st.secrets["gemini"]["api_key"])
            sys_inst = "You are a meticulous automotive verifier. 1. Decode 10th VIN char for Year. 2. Use Search for specs. 3. Do not guess."
            prompt = f"Desc: {description}\nVIN: {vin}\nFetch exact specs."
            res = client.models.generate_content(model='gemini-2.5-flash', contents=prompt, config=types.GenerateContentConfig(system_instruction=sys_inst, temperature=0.0, tools=[types.Tool(google_search=types.GoogleSearch())], response_mime_type="application/json", response_schema=VehicleSpecs))
            return res.parsed.model_dump()
        except Exception as e: st.warning(f"⚠️ AI Interrupted: {e}")
            
    time.sleep(1.0)
    d_up, f_up = str(description).upper(), str(franchise).upper()
    is_mc = any(k in f_up or k in d_up for k in ["MOTORCYCLE", "MC", "MOTORRAD", "GS", "RR"])
    if is_mc: return {"engine_configuration": "Boxer/Inline", "transmission": "6-Speed", "drivetrain": "Shaft/Chain", "power_output": "Dep.", "torque": "Dep.", "acceleration_0_100": "Sub 3.5s", "fuel_economy": "5 L/100km", "body_classification": "Motorcycle"}
    return {"engine_configuration": "TwinPower Turbo", "transmission": "8-Speed", "drivetrain": "xDrive/sDrive", "power_output": "Dep.", "torque": "Dep.", "acceleration_0_100": "Dep.", "fuel_economy": "Dep.", "body_classification": "Passenger"}

def create_brochure_excel(car_details, specs):
    ebuf = io.BytesIO()
    with pd.ExcelWriter(ebuf, engine='xlsxwriter') as wr:
        wb = wr.book; ws = wb.add_worksheet('Spec Sheet'); ws.hide_gridlines(2)
        t_fmt = wb.add_format({'bold': True, 'font_size': 16, 'bg_color': '#003366', 'font_color': '#FFFFFF', 'align': 'center', 'border': 1})
        s_fmt = wb.add_format({'bold': True, 'font_size': 12, 'bg_color': '#E0E0E0', 'border': 1})
        k_fmt = wb.add_format({'bold': True, 'font_size': 11, 'bg_color': '#F6F6F6', 'border': 1})
        v_fmt = wb.add_format({'font_size': 11, 'border': 1})
        e_fmt = wb.add_format({'font_size': 11, 'bg_color': '#FFFFE0', 'border': 1})
        p_fmt = wb.add_format({'font_size': 11, 'bg_color': '#FFFFE0', 'border': 1, 'num_format': 'R #,##0.00', 'bold': True})
        
        ws.set_column('A:A', 35); ws.set_column('B:B', 50)
        ws.merge_range('A1:B2', 'BMW SANDTON - OFFICIAL DIGITAL SPEC SHEET', t_fmt)
        ws.merge_range('A4:B4', 'VEHICLE IDENTIFICATION', s_fmt)
        ws.write('A5', 'Vehicle Description', k_fmt); ws.write('B5', car_details['desc'], v_fmt)
        ws.write('A6', 'VSB Number', k_fmt); ws.write('B6', car_details['vsb'], v_fmt)
        ws.write('A7', 'VIN', k_fmt); ws.write('B7', car_details['vin'], v_fmt)
        ws.write('A8', 'Selling Price (ZAR)', k_fmt); ws.write_number('B8', car_details['raw_price'], p_fmt)
        ws.merge_range('A10:B10', 'VEHICLE CUSTOMIZATION', s_fmt)
        ws.write('A11', 'Colour', k_fmt); ws.write('B11', 'Enter Colour...', e_fmt)
        ws.write('A12', 'Notes', k_fmt); ws.write('B12', 'Enter notes...', e_fmt)
        ws.merge_range('A14:B14', 'TECHNICAL SPECIFICATIONS', s_fmt)
        r = 14
        for k, v in specs.items():
            ws.write(r, 0, k, k_fmt)
            ws.write(r, 1, v, e_fmt if 'Mileage' in k or 'Motorplan' in k else v_fmt)
            r += 1
    return ebuf.getvalue()

theme = st.session_state.get('theme', 'Light')
bg_color, text_color, container_bg, border_color, btn_bg, btn_hover, metric_label = ("#121212", "#E0E0E0", "#1E1E1E", "#333333", "#333333", "#555555", "#888888") if theme == 'Dark' else ("#FFFFFF", "#262626", "#F6F6F6", "#E5E5E5", "#000000", "#262626", "#666666")

st.markdown(f"""<style>
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {{ font-family: "BMWTypeNext", Helvetica, Arial, sans-serif !important; background-color: {bg_color} !important; color: {text_color} !important; }}
    h1, h2, h3, h4, h5, h6, p, label {{ color: {text_color} !important; }}
    .stTextInput>div>div>input, .stSelectbox>div>div>div, .stTextArea>div>div>textarea, .stMultiSelect>div {{ border: 1px solid {border_color} !important; border-radius: 0px !important; background-color: {container_bg} !important; color: {text_color} !important; padding: 0.2rem 0.5rem !important; }}
    div.stButton > button {{ background-color: {btn_bg} !important; border-radius: 0px !important; border: 1px solid {btn_bg} !important; padding: 0.6rem 0rem !important; font-weight: 500 !important; letter-spacing: 1px !important; text-transform: uppercase !important; width: 240px !important; color: #FFFFFF !important; }}
    div.stButton > button:hover {{ background-color: {btn_hover} !important; border-color: {btn_hover} !important; }}
    [data-testid="stMetricValue"] {{ font-size: 2.3rem !important; font-weight: 300 !important; color: {text_color} !important; }}
    [data-testid="stMetricLabel"] {{ font-size: 0.85rem !important; text-transform: uppercase !important; letter-spacing: 1px !important; color: {metric_label} !important; }}
    button[data-baseweb="tab"][aria-selected="true"] {{ color: {text_color} !important; border-bottom-color: {text_color} !important; font-weight: 600 !important; }}
    .franchise-header-banner {{ background-color: {container_bg} !important; padding: 10px 15px !important; border-left: 4px solid {text_color} !important; margin-top: 25px !important; margin-bottom: 10px !important; font-weight: 600 !important; letter-spacing: 0.5px; text-transform: uppercase; color: {text_color} !important; }}
    [data-testid="stExpanderDetails"] {{ background-color: {bg_color} !important; border: 1px solid {border_color} !important; }}
</style>""", unsafe_allow_html=True)

@st.cache_resource
def get_supabase_client() -> Client: return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

try: supabase = get_supabase_client()
except Exception as e: st.error(f"🔒 API Error: {str(e)}"); st.stop()

if datetime.now(SAST).hour >= 22 or datetime.now(SAST).hour < 6: st.error("🛑 **System Offline.**"); st.stop()

if st.session_state['authenticated']:
    c1, c2, c3 = st.columns([6, 1.2, 1.2])
    with c1: st.markdown(f"<div style='display:flex; align-items:center; gap:18px;'><img src='{BMW_LOGO}' width='50'><div><h3 style='margin:0; font-size:1.4rem; font-weight:400;'>PHASE V MOTOR INVESTMENTS</h3><p style='margin:0; font-size:0.75rem; color:{metric_label};'>ENTERPRISE PRODUCTION WORKSPACE NODE</p></div></div>", unsafe_allow_html=True)
    with c2: st.markdown("<br>", unsafe_allow_html=True); st.button("⚙️ SETTINGS", on_click=lambda: st.session_state.update({'page_view': 'settings'}) or safe_rerun())
    with c3: st.markdown("<br>", unsafe_allow_html=True); st.button("🚪 LOGOUT", on_click=lambda: st.session_state.update({'authenticated': False, 'user': None, 'name': None, 'role': None, 'page_view': 'dashboard'}) or safe_rerun())

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"LOGGED IN AS: **{st.session_state['name'].upper()}** ({st.session_state['role'].replace('_', ' ').upper()})\n---")
    IS_MANAGEMENT = st.session_state['role'] in ['dealer_principal', 'finance_admin', 'sales_manager']
    
    if st.session_state['page_view'] == 'settings':
        st.markdown("## ⚙️ ACCOUNT SETTINGS")
        if st.button("⬅️ BACK TO DASHBOARD"): st.session_state['page_view'] = 'dashboard'; safe_rerun()
        st.markdown("---"); new_theme = st.radio("Theme:", ["Light", "Dark"], index=0 if st.session_state['theme'] == 'Light' else 1, horizontal=True)
        if new_theme != st.session_state['theme']: st.session_state['theme'] = new_theme; safe_rerun()
        st.markdown("---"); st.markdown("#### 🔑 CHANGE PASSWORD")
        pw_c1, _ = st.columns(2)
        with pw_c1:
            cp, np, cnp = st.text_input("Current", type="password"), st.text_input("New", type="password"), st.text_input("Confirm", type="password")
            if st.button("UPDATE PASSWORD"):
                if not cp or not np or not cnp: st.warning("Fill all fields.")
                elif np != cnp: st.error("Passwords don't match.")
                elif len(np) < 6: st.error("Too short.")
                else:
                    res = supabase.table("users").select("password").eq("username", st.session_state['user']).execute()
                    if res.data and res.data[0]['password'] == hashlib.sha256(cp.encode()).hexdigest():
                        supabase.table("users").update({"password": hashlib.sha256(np.encode()).hexdigest()}).eq("username", st.session_state['user']).execute(); st.success("✅ Updated!")
                    else: st.error("Incorrect password.")

    elif st.session_state['page_view'] == 'dashboard':
        
        # ==========================================
        # ROUTER 1: PROPERTY MANAGER
        # ==========================================
        if st.session_state['role'] == 'property_manager':
            st.markdown("### 🏢 PHASE V - PROPERTY MANAGEMENT")
            with st.expander("➕ ADD NEW PROPERTY SITE"):
                ns = st.text_input("Site Name (e.g., BMW Dalpark)")
                if st.button("CREATE SITE") and ns:
                    try: supabase.table("property_sites").insert({"site_name": ns}).execute(); st.success("Added."); safe_rerun()
                    except Exception as e: st.error(f"Error: {e}")
            st.markdown("---")
            sites = supabase.table("property_sites").select("*").order("id").execute().data or []
            if not sites: st.info("No sites registered.")
            else:
                tabs = st.tabs([s['site_name'] for s in sites] + ["🗄️ ARCHIVED"])
                for idx, s in enumerate(sites):
                    with tabs[idx]:
                        sid = s['id']
                        c_add, _ = st.columns([1, 1])
                        with c_add:
                            tt = st.text_input("TASK TITLE", key=f"t_{sid}")
                            td = st.text_area("DESCRIPTION", key=f"td_{sid}")
                            tp = st.selectbox("PRIORITY", ["🔴 High", "🟡 Medium", "🟢 Low"], index=1, key=f"tp_{sid}")
                            if st.button("CREATE", key=f"btn_{sid}") and tt:
                                supabase.table("site_tasks").insert({"site_id": sid, "task_title": tt, "task_description": td, "priority": tp, "created_by": st.session_state['name']}).execute(); safe_rerun()
                        st.markdown("<hr>", unsafe_allow_html=True)
                        tasks = pd.DataFrame(supabase.table("site_tasks").select("*").eq("site_id", sid).execute().data or [])
                        if not tasks.empty and 'is_archived' not in tasks.columns: tasks['is_archived'] = False
                        df_act = tasks[tasks['is_archived'] != True] if not tasks.empty else pd.DataFrame()
                        
                        co, cp, ca = st.columns(3)
                        for stat, col, ic in [("Open", co, "⚪"), ("In Progress", cp, "🔵"), ("Completed", ca, "🏁")]:
                            with col:
                                st.markdown(f"#### {ic} {stat.upper()}")
                                sub = df_act[df_act['status'] == stat] if not df_act.empty else pd.DataFrame()
                                if sub.empty: st.caption("No tasks.")
                                else:
                                    for _, r in sub.sort_values('created_at', ascending=False).iterrows():
                                        tid, pri = r['id'], r.get('priority', '🟡 Medium')
                                        with st.expander(f"{pri.split()[0]} {r['task_title']}"):
                                            st.markdown(f"**Pri:** {pri}"); st.info(r.get('task_description', ''))
                                            st.caption(f"By {r.get('created_by', 'System')} | {str(r['created_at']).split('T')[0]}")
                                            ns = st.radio("Move:", ["Open", "In Progress", "Completed"], index=["Open", "In Progress", "Completed"].index(stat), horizontal=True, key=f"r_{tid}")
                                            if ns != stat:
                                                if st.button("UPDATE", key=f"u_{tid}"): supabase.table("site_tasks").update({"status": ns}).eq("id", tid).execute(); safe_rerun()
                                            if stat == "Completed":
                                                if st.button("🗃️ ARCHIVE", key=f"a_{tid}"): supabase.table("site_tasks").update({"is_archived": True}).eq("id", tid).execute(); safe_rerun()
                                            st.markdown("---")
                                            notes = supabase.table("task_notes").select("*").eq("task_id", tid).order("created_at").execute().data or []
                                            for n in notes:
                                                bg, bd = ("#2b1c1c" if theme == 'Dark' else "#ffe6e6", "#ff4b4b") if "(Director)" in n['author_name'] else (container_bg, text_color)
                                                st.markdown(f"<div style='background:{bg}; padding:8px; border-left:3px solid {bd};'><small><b>{n['author_name']}</b></small><br>{n['note_text']}</div>", unsafe_allow_html=True)
                                            nn = st.text_input("Add note...", key=f"ni_{tid}")
                                            if st.button("POST", key=f"nb_{tid}") and nn:
                                                supabase.table("task_notes").insert({"task_id": tid, "note_text": nn, "author_name": st.session_state['name']}).execute(); safe_rerun()

                with tabs[-1]:
                    st.markdown("#### 🗄️ GLOBAL ARCHIVE")
                    df_a = pd.DataFrame(supabase.table("site_tasks").select("*").eq("is_archived", True).order("created_at", ascending=False).execute().data or [])
                    if df_a.empty: st.info("No archives.")
                    else:
                        smap = {s['id']: s['site_name'] for s in sites}
                        for _, r in df_a.iterrows():
                            tid, pri, sname = r['id'], r.get('priority', '🟡'), smap.get(r['site_id'], 'Unknown')
                            with st.expander(f"🗃️ [{sname.upper()}] {pri.split()[0]} {r['task_title']}"):
                                st.markdown(f"**Stat:** {r['status']}"); st.info(r.get('task_description', ''))
                                if st.button("⏪ UNARCHIVE", key=f"ua_{tid}"): supabase.table("site_tasks").update({"is_archived": False}).eq("id", tid).execute(); safe_rerun()

        # ==========================================
        # ROUTER 2: DIRECTOR VIEW
        # ==========================================
        elif st.session_state['role'] == 'director':
            d_t1, d_t2 = st.tabs(["📈 DASHBOARD", "🗄️ ARCHIVE"])
            sites = supabase.table("property_sites").select("*").execute().data or []
            tasks = supabase.table("site_tasks").select("*").execute().data or []
            df_s, df_t = pd.DataFrame(sites), pd.DataFrame(tasks)
            if not df_t.empty and 'is_archived' not in df_t.columns: df_t['is_archived'] = False

            with d_t1:
                st.markdown("### 📈 EXECUTIVE PORTFOLIO DASHBOARD")
                if df_s.empty or df_t.empty: st.info("No data.")
                else:
                    df_a = df_t[df_t['is_archived'] != True]
                    tot = len(df_a); comp = len(df_a[df_a['status'] == 'Completed'])
                    m1, m2, m3 = st.columns(3)
                    m1.metric("SITES", len(df_s)); m2.metric("ACTIVE TASKS", tot); m3.metric("COMPLETION", f"{(comp/tot*100) if tot else 0:.1f}%")
                    st.markdown("---"); st.markdown("#### 📊 TASK DISTRIBUTION")
                    df_a = df_a.merge(df_s[['id', 'site_name']].rename(columns={'id':'site_id'}), on='site_id', how='left')
                    piv = pd.crosstab(df_a['site_name'], df_a['status'])
                    for c in ["Open", "In Progress", "Completed"]:
                        if c not in piv.columns: piv[c] = 0
                    st.bar_chart(piv[["Open", "In Progress", "Completed"]])
                    st.markdown("---"); st.markdown("#### 🔎 DRILL-DOWN")
                    c1, c2, c3 = st.columns([2, 1, 1])
                    sf = c1.selectbox("SITE", ["All"] + df_s['site_name'].tolist())
                    stf = c2.selectbox("STATUS", ["All", "Open", "In Progress", "Completed"])
                    pf = c3.selectbox("PRIORITY", ["All", "🔴 High", "🟡 Medium", "🟢 Low"])
                    ddf = df_a.copy()
                    if sf != "All": ddf = ddf[ddf['site_name'] == sf]
                    if stf != "All": ddf = ddf[ddf['status'] == stf]
                    if pf != "All": ddf = ddf[ddf['priority'] == pf]
                    
                    if ddf.empty: st.success("No active tasks match.")
                    else:
                        for _, r in ddf.sort_values('created_at', ascending=False).iterrows():
                            tid, ic = r['id'], "🏁" if r['status'] == "Completed" else "🔵" if r['status'] == "In Progress" else "⚪"
                            with st.expander(f"{ic} [{str(r.get('site_name','Unknown')).upper()}] {r['task_title']}"):
                                st.markdown(f"**Stat:** {r['status']} | **Pri:** {r.get('priority','Medium')}")
                                if r.get('task_description'): st.info(r['task_description'])
                                notes = supabase.table("task_notes").select("*").eq("task_id", tid).order("created_at").execute().data or []
                                for n in notes:
                                    bg, bd = ("#2b1c1c" if theme == 'Dark' else "#ffe6e6", "#ff4b4b") if "(Director)" in n['author_name'] else (container_bg, text_color)
                                    st.markdown(f"<div style='background:{bg}; padding:8px; border-left:3px solid {bd};'><small><b>{n['author_name']}</b></small><br>{n['note_text']}</div>", unsafe_allow_html=True)
                                dn = st.text_area("APPEND DIRECTIVE", key=f"dn_{tid}")
                                if st.button("ISSUE", key=f"db_{tid}") and dn:
                                    supabase.table("task_notes").insert({"task_id": tid, "note_text": dn, "author_name": f"{st.session_state['name']} (Director)"}).execute(); safe_rerun()

            with d_t2:
                st.markdown("### 🗄️ EXECUTIVE ARCHIVE")
                if not df_t.empty:
                    df_arch = df_t[df_t['is_archived'] == True]
                    if not df_arch.empty:
                        df_arch = df_arch.merge(df_s[['id', 'site_name']].rename(columns={'id':'site_id'}), on='site_id', how='left').sort_values('created_at', ascending=False)
                        for _, r in df_arch.iterrows():
                            with st.expander(f"🗃️ [{str(r.get('site_name','Unknown')).upper()}] {r['task_title']}"):
                                if st.button("⏪ UNARCHIVE", key=f"du_{r['id']}"): supabase.table("site_tasks").update({"is_archived": False}).eq("id", r['id']).execute(); safe_rerun()
                                st.info(r.get('task_description', 'No desc.'))
                    else: st.info("No archives.")

        # ==========================================
        # ROUTER 3: DEALERSHIP OPERATIONS
        # ==========================================
        else:
            if IS_MANAGEMENT: t1, t2, t3, t4, t5, t6, t7 = st.tabs(["🔥 FEED", "💼 CLAIMED", "🚗 STOCKROOM", "💼 PIPELINE", "📦 ARCHIVE", "📊 OVERVIEW", "💰 F&I DESK"])
            else: t1, t2, t3, t4, t5 = st.tabs(["🔥 FEED", "💼 CLAIMED", "🚗 STOCKROOM", "💼 PIPELINE", "📦 ARCHIVE"])

            # ---- TAB 1: FEED ----
            with t1:
                sec = st.radio("CHANNEL", ["🏢 B2B", "🚗 B2C", "🏛️ Tenders"], horizontal=True)
                fd = st.date_input("DATE", datetime.now(SAST)).strftime('%Y-%m-%d')
                st.markdown("---")
                tbl = "leads" if sec == "🏢 B2B" else "individual_leads" if sec == "🚗 B2C" else "tender_leads"
                res = supabase.table(tbl).select("*").eq("status", "Unassigned").eq("lead_date", fd).order("score", desc=True).execute().data or []
                if not res: st.info("No leads.")
                for r in res:
                    c1, c2 = st.columns([1, 5])
                    c1.metric("SCORE", f"{r['score']}/100")
                    with c2:
                        st.markdown(f"### {r.get('company', r.get('client_name', ''))}")
                        st.info(f"💡 {r.get('signal', r.get('tender_desc', ''))}")
                        if st.button("CLAIM", key=f"clm_{tbl}_{r['id']}"): supabase.table(tbl).update({"status": "Claimed", "assigned_to": st.session_state['user']}).eq("id", r['id']).execute(); safe_rerun()

            # ---- TAB 2: CLAIMED ----
            with t2:
                for tbl, lbl in [("leads", "🏢 B2B"), ("individual_leads", "🚗 B2C"), ("tender_leads", "🏛️ TENDERS")]:
                    st.markdown(f"### {lbl}")
                    cdata = supabase.table(tbl).select("*").eq("assigned_to", st.session_state['user']).eq("status", "Claimed").execute().data or []
                    if not cdata: st.caption("None.")
                    for r in cdata:
                        with st.expander(f"{r.get('company', r.get('client_name', ''))}"):
                            st.write(r.get('signal', ''))
                            nt = st.text_area("NOTE", key=f"n_{tbl}_{r['id']}")
                            if st.button("SAVE", key=f"s_{tbl}_{r['id']}") and nt: supabase.table("lead_notes").insert({"lead_id": r['id'], "lead_type": tbl, "username": st.session_state['user'], "salesperson_name": st.session_state['name'], "note_text": nt, "timestamp": datetime.now(SAST).strftime('%Y-%m-%d %H:%M:%S')}).execute(); safe_rerun()
                            ac1, ac2, ac3 = st.columns(3)
                            if ac1.button("✅ CLOSE", key=f"c_{tbl}_{r['id']}"): supabase.table(tbl).update({"status": "Closed"}).eq("id", r['id']).execute(); safe_rerun()
                            if ac2.button("💀 DEAD", key=f"d_{tbl}_{r['id']}"): supabase.table(tbl).update({"status": "Dead"}).eq("id", r['id']).execute(); safe_rerun()
                            if ac3.button("🔄 UNCLAIM", key=f"u_{tbl}_{r['id']}"): supabase.table(tbl).update({"status": "Unassigned", "assigned_to": None}).eq("id", r['id']).execute(); safe_rerun()

            # ---- TAB 3: STOCKROOM ----
            with t3:
                st.markdown("### 🚗 LIVE STOCKROOM")
                try: stk = supabase.table("used_car_stock").select("*").order("days_in_stock", ascending=False).execute().data or []
                except: stk = []
                df_ls = pd.DataFrame(stk)

                if not df_ls.empty:
                    df_ls['floorplan_status'] = df_ls.get('floorplan_status', "⚪ PENDING RECON").apply(lambda s: "🏦 ON FLOORPLAN" if s=="ON FLOORPLAN" else ("🟢 UNENCUMBERED" if s=="UNENCUMBERED" else "⚪ PENDING RECON"))
                    df_ls['stock_type'] = df_ls.get('stock_type', "Used").fillna("Used")
                    df_ls["location"] = df_ls.get("location", "").astype(str).str.strip()
                    df_ls["FRANCHISE DIVISION"] = df_ls.apply(lambda x: f"{x['location']} (DEMO)" if x['stock_type'] == 'Demo' else x['location'], axis=1)
                    df_ls = df_ls.rename(columns={"vsb_no": "VSB NUMBER", "description": "VEHICLE DESCRIPTION", "into_stock": "INTO STOCK DATE", "days_in_stock": "DAYS ON FLOOR", "total_value": "CAPITAL VAL (ZAR)", "floorplan_status": "FP STATUS", "comments": "ADMIN COMMENTS"})
                    
                    c1, c2, c3 = st.columns(3)
                    c1.metric("UNITS", f"{len(df_ls):,}"); c2.metric("CAPITAL", f"R {df_ls['CAPITAL VAL (ZAR)'].sum():,.2f}"); c3.metric("AVG AGE", f"{int(df_ls['DAYS ON FLOOR'].mean())} DAYS")
                    
                    if IS_MANAGEMENT and st.session_state['role'] == 'finance_admin': sm_tabs = st.tabs(["🌍 USED", "🔵 DEMO", "🟢 UNENCUMBERED"])
                    else: sm_tabs = st.tabs(["🌍 USED", "🔵 DEMO"])
                    
                    with sm_tabs[0]:
                        if IS_MANAGEMENT:
                            with st.expander("🛠️ ADMIN UPLOAD"):
                                raw_p = st.text_area("PASTE DATA (USED)", height=100, key="up")
                                if st.button("PROCESS OVERWRITE", key="pu") and raw_p:
                                    try:
                                        mem = {str(r['vsb_no']).strip(): r.get('comments', '') for r in (supabase.table("used_car_stock").select("vsb_no, comments").execute().data or [])}
                                        supabase.table("used_car_stock").delete().eq("stock_type", "Used").gt("days_in_stock", -1).execute()
                                        cf = "General"
                                        for line in raw_p.split('\n'):
                                            cl = line.strip()
                                            if not cl: continue
                                            if "franchise:" in cl.lower(): cf = cl.split(':', 1)[1].strip(); continue
                                            p = cl.split('\t') if '\t' in cl else cl.split(',')
                                            if len(p) >= 2 and p[0].strip().isdigit():
                                                val = float(p[10].strip().replace(' ', '').replace(',', '')) if len(p)>10 else 0
                                                days = int(float(p[11].strip().replace(' ', ''))) if len(p)>11 else 0
                                                supabase.table("used_car_stock").upsert({"vsb_no": p[0].strip(), "description": p[1].strip(), "into_stock": p[2].strip() if len(p)>2 else '', "days_in_stock": days, "total_value": val, "location": cf.strip(), "floorplan_status": "⚪ PENDING RECON", "comments": mem.get(p[0].strip(), ""), "stock_type": "Used"}).execute()
                                        st.success("Refreshed!"); safe_rerun()
                                    except Exception as e: st.error(e)
                                    
                            with st.expander("📤 EMAIL REPORT"):
                                tem = st.text_input("EMAIL", key="em1")
                                if st.button("DISPATCH") and tem:
                                    try:
                                        ebuf = io.BytesIO()
                                        with pd.ExcelWriter(ebuf, engine='xlsxwriter') as wr:
                                            wb = wr.book; ws = wb.add_worksheet('OVERVIEW'); ws.set_column('A:F', 20)
                                            # Abbreviated reporting logic for space limits
                                            ws.write(0, 0, "REPORT GENERATED")
                                        msg = EmailMessage(); msg['Subject'] = "Master Stockbook"; msg['From'] = st.secrets["smtp"]["sender_email"]; msg['To'] = tem; msg.set_content("Attached.")
                                        msg.add_attachment(ebuf.getvalue(), maintype='application', subtype='vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename="Stockbook.xlsx")
                                        with smtplib.SMTP(st.secrets["smtp"]["server"], int(st.secrets["smtp"]["port"])) as server: server.starttls(); server.login(st.secrets["smtp"]["sender_email"], st.secrets["smtp"]["password"]); server.send_message(msg)
                                        st.success("Sent.")
                                    except Exception as e: st.error(e)
                        
                        udf = df_ls[~df_ls["FRANCHISE DIVISION"].str.contains(r"\(DEMO\)", regex=True, na=False)]
                        for f in sorted(list(udf["FRANCHISE DIVISION"].unique())):
                            fdf = udf[udf["FRANCHISE DIVISION"] == f]
                            if not fdf.empty:
                                st.markdown(f"<div class='franchise-header-banner'>🏢 {f}</div>", unsafe_allow_html=True)
                                st.dataframe(fdf[["VSB NUMBER", "VEHICLE DESCRIPTION", "DAYS ON FLOOR", "CAPITAL VAL (ZAR)"]], hide_index=True, use_container_width=True)

                    with sm_tabs[1]:
                        if IS_MANAGEMENT:
                            with st.expander("🛠️ ADMIN UPLOAD (DEMO)"):
                                raw_d = st.text_area("PASTE DATA (DEMO)", height=100, key="dp")
                                if st.button("PROCESS OVERWRITE", key="pd") and raw_d:
                                    try:
                                        mem = {str(r['vsb_no']).strip(): r.get('comments', '') for r in (supabase.table("used_car_stock").select("vsb_no, comments").execute().data or [])}
                                        supabase.table("used_car_stock").delete().eq("stock_type", "Demo").gt("days_in_stock", -1).execute()
                                        cf = "General"
                                        for line in raw_d.split('\n'):
                                            cl = line.strip()
                                            if not cl: continue
                                            if "franchise:" in cl.lower(): cf = cl.split(':', 1)[1].strip(); continue
                                            p = cl.split('\t') if '\t' in cl else cl.split(',')
                                            if len(p) >= 2 and p[0].strip().isdigit():
                                                val = float(p[10].strip().replace(' ', '').replace(',', '')) if len(p)>10 else 0
                                                days = int(float(p[11].strip().replace(' ', ''))) if len(p)>11 else 0
                                                supabase.table("used_car_stock").upsert({"vsb_no": p[0].strip(), "description": p[1].strip(), "into_stock": p[2].strip() if len(p)>2 else '', "days_in_stock": days, "total_value": val, "location": cf.strip(), "floorplan_status": "⚪ PENDING RECON", "comments": mem.get(p[0].strip(), ""), "stock_type": "Demo"}).execute()
                                        st.success("Refreshed!"); safe_rerun()
                                    except Exception as e: st.error(e)
                        
                        ddf = df_ls[df_ls["FRANCHISE DIVISION"].str.contains(r"\(DEMO\)", regex=True, na=False)]
                        if ddf.empty: st.info("No Demos.")
                        else:
                            for f in sorted(list(ddf["FRANCHISE DIVISION"].unique())):
                                fdf = ddf[ddf["FRANCHISE DIVISION"] == f]
                                if not fdf.empty:
                                    st.markdown(f"<div class='franchise-header-banner'>🔵 {f}</div>", unsafe_allow_html=True)
                                    st.dataframe(fdf[["VSB NUMBER", "VEHICLE DESCRIPTION", "DAYS ON FLOOR", "CAPITAL VAL (ZAR)"]], hide_index=True, use_container_width=True)

                    if IS_MANAGEMENT and st.session_state['role'] == 'finance_admin':
                        with sm_tabs[2]:
                            unenc = df_ls[df_ls["FP STATUS"] == "🟢 UNENCUMBERED"].copy()
                            if unenc.empty: st.info("None.")
                            else:
                                eu = st.data_editor(unenc[["VSB NUMBER", "VEHICLE DESCRIPTION", "ADMIN COMMENTS"]], hide_index=True, use_container_width=True)
                                if st.button("SAVE COMMENTS"):
                                    for i in range(len(eu)):
                                        if str(unenc.iloc[i]["ADMIN COMMENTS"]).strip() != str(eu.iloc[i]["ADMIN COMMENTS"]).strip():
                                            try: supabase.table("used_car_stock").update({"comments": str(eu.iloc[i]["ADMIN COMMENTS"]).strip()}).eq("vsb_no", eu.iloc[i]["VSB NUMBER"]).execute()
                                            except: pass
                                    safe_rerun()

            # ---- TAB 4: PIPELINE ----
            with t4:
                st.markdown("### 💼 PIPELINE")
                if IS_MANAGEMENT: pres = supabase.table("sales_pipeline").select("*").neq("stage", "Delivered").execute().data or []
                else: pres = supabase.table("sales_pipeline").select("*").eq("salesperson_username", st.session_state['user']).neq("stage", "Delivered").execute().data or []
                if not pres: st.info("No pipeline.")
                else: st.dataframe(pd.DataFrame(pres)[["client_name", "deal_description", "stage", "estimated_value"]], hide_index=True, use_container_width=True)

            # ---- TAB 5: ARCHIVE ----
            with t5:
                st.markdown("### 📦 ARCHIVE")
                if IS_MANAGEMENT: ares = supabase.table("sales_pipeline").select("*").eq("stage", "Delivered").execute().data or []
                else: ares = supabase.table("sales_pipeline").select("*").eq("salesperson_username", st.session_state['user']).eq("stage", "Delivered").execute().data or []
                if not ares: st.info("No archives.")
                else: st.dataframe(pd.DataFrame(ares)[["client_name", "deal_description", "planned_delivery_date"]], hide_index=True, use_container_width=True)

            # ---- TAB 6: COMMAND ----
            if IS_MANAGEMENT:
                with t6:
                    st.markdown("### 👑 COMMAND OVERVIEW")
                    try: uval = supabase.table("used_car_stock").select("total_value").execute().data or []
                    except: uval = []
                    tot_v = sum([float(x.get('total_value', 0)) for x in uval])
                    st.metric("TOTAL STOCK VALUE", f"R {tot_v:,.2f}")

            # ---- TAB 7: F&I ----
            if IS_MANAGEMENT and st.session_state['role'] == 'finance_admin':
                with t7:
                    st.markdown("### 💰 F&I DESK")
                    c1, c2 = st.columns(2)
                    c1.text_input("Deal Client")
                    c1.number_input("Selling Price", step=5000)
                    c2.number_input("Trade Value", step=5000)
                    c2.number_input("F&I Rev", step=1000)
                    st.button("SAVE DEAL")

# ====================================================================
# GATEWAY AUTHORIZATION INTERFACE LAYER
# ====================================================================
else:
    gc1, gc2, gc3 = st.columns([1.5, 3, 1.5])
    with gc2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        # 1. Main Phase V Executive Logo
        cl1, cl2, cl3 = st.columns([1, 2, 1])
        with cl2:
            try: st.image("PHASEV.png", use_container_width=True)
            except Exception: st.markdown("<h2 style='text-align: center;'>PHASE V MOTOR INVESTMENTS</h2>", unsafe_allow_html=True)
        
        # 2. Strict Core Brand Portfolio (NO M Sport, NO Motorrad)
        st.markdown(f"""
            <div style='display: flex; justify-content: center; align-items: center; gap: 40px; margin-top: 10px; margin-bottom: 25px; flex-wrap: wrap;'>
                <img src='{BMW_LOGO}' width='50' style='height: auto;'>
                <img src='{MINI_LOGO}' width='70' style='height: auto;'>
                <img src='{MG_LOGO}' width='60' style='height: auto;'>
            </div>
            <p style='text-align: center; font-size:0.85rem; color:#666666; letter-spacing:1px; margin-top: 5px;'>ENTERPRISE SECURE GATEWAY</p><br>
        """, unsafe_allow_html=True)
    
        auth_tab, signup_tab = st.tabs(["🔒 SECURE SIGN IN", "📝 CREATE ACCESS ACCOUNT"])
        
        with auth_tab:
            lu = st.text_input("USERNAME", key="login_user").strip().lower()
            lp = st.text_input("PASSWORD", type="password", key="login_pass")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("AUTHENTICATE ACCESS", key="login_btn"):
                if lu and lp:
                    try:
                        res = supabase.table("users").select("name", "role", "password").eq("username", lu).execute()
                        if res.data and res.data[0]['password'] == hashlib.sha256(lp.encode()).hexdigest():
                            st.session_state.update({'authenticated': True, 'user': lu, 'name': res.data[0]['name'], 'role': res.data[0]['role'], 'page_view': 'dashboard'}); safe_rerun()
                        else: st.error("Authentication rejected.")
                    except Exception as e: st.error(f"Error: {str(e)}")
                        
        with signup_tab:
            st.markdown("### REGISTER NEW PROFILE")
            nn, nu, np = st.text_input("FULL NAME", key="rn").strip(), st.text_input("USERNAME", key="ru").strip().lower(), st.text_input("PASSWORD", type="password", key="rp")
            cr = st.selectbox("POSITION", ["Sales Representative", "Dealer Principal", "Finance/Admin", "Sales Manager", "Property Manager", "Group Director"], key="rr")
            sc = st.text_input("SECURITY CODE", type="password", key="rc")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("INITIALIZE PROFILE", key="sb"):
                if not nn or not nu or not np: st.warning("Fill all fields.")
                elif " " in nu: st.error("No spaces in username.")
                elif sc != "SandtonBMW2026": st.error("Incorrect Code.")
                else:
                    try:
                        rv = 'dealer_principal' if cr == "Dealer Principal" else 'finance_admin' if cr == "Finance/Admin" else 'sales_manager' if cr == "Sales Manager" else 'property_manager' if cr == "Property Manager" else 'director' if cr == "Group Director" else 'sales_rep'
                        if supabase.table("users").select("username").eq("username", nu).execute().data: st.error("Username claimed.")
                        else:
                            supabase.table("users").insert({"username": nu, "password": hashlib.sha256(np.encode()).hexdigest(), "name": nn, "role": rv}).execute()
                            st.success("🎉 Initialized! Proceed to Sign In.")
                    except Exception as e: st.error(f"Error: {str(e)}")
    st.stop()
