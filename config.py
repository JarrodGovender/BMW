import streamlit as st
import pandas as pd
from datetime import datetime
import pytz
import os
import io
import time
import base64
from supabase import create_client

SAST = pytz.timezone('Africa/Johannesburg')

# --- 1. AI SCHEMA ---
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

# --- 2. ASSET LOADER ---
def get_local_img(file_name, cdn_fallback):
    if os.path.exists(file_name):
        try:
            with open(file_name, "rb") as f:
                return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
        except Exception: return cdn_fallback
    return cdn_fallback

BMW_LOGO = get_local_img("assets/BMW.png", "https://upload.wikimedia.org/wikipedia/commons/4/44/BMW.svg")
MINI_LOGO = get_local_img("assets/MINI.png", "https://upload.wikimedia.org/wikipedia/commons/e/ea/MINI_logo.svg")
MG_LOGO = get_local_img("assets/MG.png", "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/MG_logo.svg/512px-MG_logo.svg.png")
PHASEV_LOGO = get_local_img("assets/PHASEV.png", "")

# --- 3. DATABASE INITIALIZATION ---
@st.cache_resource
def get_supabase_client():
    return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])

def safe_rerun():
    st.rerun() if hasattr(st, "rerun") else st.experimental_rerun()

# --- STATIC REFERENCE DATA (cached) ---
@st.cache_data(ttl=300)
def get_static_reference_data(_supabase):
    fallbacks = {
        "roles": ["SALES_REP", "SALES_MANAGER", "FINANCE_ADMIN", "DEALER_PRINCIPAL", "DIRECTOR", "SUPER_USER", "WORKSHOP_MANAGER", "PARTS_MANAGER", "HR_ADMIN"],
        "locations": ["BMW_SANDTON", "BMW_BEDFORDVIEW", "BMW_EASTRAND", "BMW_DALPARK", "MF_SANDTON", "MF_FOURWAYS", "GLOBAL_HQ"],
        "departments": ["NEW_SALES", "USED_SALES", "SERVICE", "PARTS", "FINANCE", "HR", "ALL_DEPTS"],
        "brands": ["BMW", "MINI", "MOTORRAD", "MG", "HONDA", "JAC", "ALL_BRANDS"],
    }
    data = {}
    for key, table in [("roles", "roles"), ("locations", "locations"), ("departments", "departments"), ("brands", "brands")]:
        try:
            data[key] = [row['id'] for row in _supabase.table(table).select("id").execute().data]
        except Exception:
            data[key] = fallbacks[key]
    return data

# --- 4. GLOBAL CSS STYLING ---
def apply_theme():
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
    return text_color, container_bg, metric_label, border_color, theme

# --- 5. ENGINES (AI & Excel) ---
def get_ai_vehicle_specs(description, franchise, vin):
    has_key = "gemini" in st.secrets and "api_key" in st.secrets["gemini"]
    if GEMINI_AVAILABLE and has_key:
        try:
            client = genai.Client(api_key=st.secrets["gemini"]["api_key"])
            sys_inst = "You are a meticulous automotive verifier. Decode VIN and Search. Never guess."
            prompt = f"Desc: {description}\nVIN: {vin}\nFetch exact specs."
            res = client.models.generate_content(model='gemini-2.5-flash', contents=prompt, config=types.GenerateContentConfig(system_instruction=sys_inst, temperature=0.0, tools=[types.Tool(google_search=types.GoogleSearch())], response_mime_type="application/json", response_schema=VehicleSpecs))
            return res.parsed.model_dump()
        except: pass
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
        k_fmt = wb.add_format({'bold': True, 'border': 1, 'bg_color': '#F6F6F6'})
        v_fmt = wb.add_format({'border': 1})
        e_fmt = wb.add_format({'border': 1, 'bg_color': '#FFFFE0'})
        p_fmt = wb.add_format({'border': 1, 'bg_color': '#FFFFE0', 'num_format': 'R #,##0.00', 'bold': True})
        
        ws.set_column('A:A', 35); ws.set_column('B:B', 50)
        ws.merge_range('A1:B2', 'PHASE V MOTOR INVESTMENTS - OFFICIAL DIGITAL SPEC SHEET', t_fmt)
        ws.merge_range('A4:B4', 'VEHICLE IDENTIFICATION', s_fmt)
        ws.write('A5', 'Vehicle Description', k_fmt); ws.write('B5', car_details['desc'], v_fmt)
        ws.write('A6', 'VSB Number', k_fmt); ws.write('B6', car_details['vsb'], v_fmt)
        ws.write('A7', 'VIN', k_fmt); ws.write('B7', car_details['vin'], v_fmt)
        ws.write('A8', 'Selling Price', k_fmt); ws.write_number('B8', car_details['raw_price'], p_fmt)
        ws.merge_range('A10:B10', 'VEHICLE CUSTOMIZATION', s_fmt)
        ws.write('A11', 'Colour', k_fmt); ws.write('B11', 'Enter Colour...', e_fmt)
        ws.write('A12', 'Notes', k_fmt); ws.write('B12', 'Enter notes...', e_fmt)
        ws.merge_range('A14:B14', 'TECHNICAL SPECIFICATIONS', s_fmt)
        r = 14
        for k, v in specs.items():
            ws.write(r, 0, k, k_fmt); ws.write(r, 1, v, e_fmt if 'Mileage' in k or 'Motorplan' in k else v_fmt); r += 1
    return ebuf.getvalue()
