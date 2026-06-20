import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from config import BMW_LOGO, MINI_LOGO, MG_LOGO, SAST
from utils.helpers import fmt_currency
from utils import demo_data

TARGET_DEALERS = [
    "BMW Bedfordview",
    "BMW Sandton",
    "BMW East Rand",
    "BMW Dalpark",
    "MF Sandton",
    "MF Fourways",
]

DEALER_MAP = {
    'BMW_BEDFORDVIEW': 'BMW Bedfordview',
    'BMW_SANDTON': 'BMW Sandton',
    'BMW_EASTRAND': 'BMW East Rand',
    'BMW_DALPARK': 'BMW Dalpark',
    'MF_SANDTON': 'MF Sandton',
    'MF_FOURWAYS': 'MF Fourways',
}

PODIUM_RANK_COLORS = {1: "#FFD700", 2: "#C0C0C0", 3: "#CD7F32"}


# ====================================================================
# DATA LAYER — single round of fetches, reused by every panel below
# (the mockup-aligned dashboard AND the legacy detail rollups). When
# presentation_mode is on, Supabase is never called: synthetic rows from
# utils/demo_data.py are run through this exact same cleaning/aggregation
# code instead, so a demo and a live render are visually identical in
# structure and there's zero risk of a network error or empty table
# surfacing mid-presentation.
# ====================================================================
def _fetch_data(supabase, presentation_mode):
    out = {}

    if presentation_mode:
        stock = pd.DataFrame(demo_data.get_demo_stock_rows())
    else:
        try:
            stock = pd.DataFrame(supabase.table("used_car_stock")
                                  .select("location_id, total_value, days_in_stock, floorplan_status")
                                  .execute().data)
        except Exception as e:
            st.error(f"Failed to load stock data: {e}")
            stock = pd.DataFrame()
    if not stock.empty:
        stock['total_value'] = pd.to_numeric(stock['total_value'], errors='coerce').fillna(0.0)
        stock['days_in_stock'] = pd.to_numeric(stock['days_in_stock'], errors='coerce').fillna(0)
        stock['floorplan_status'] = stock['floorplan_status'].astype(str).str.upper()
        stock['is_unencumbered'] = stock['floorplan_status'].str.contains('UNENCUMBERED', na=False)
        stock['unencumbered_value'] = stock.apply(lambda r: r['total_value'] if r['is_unencumbered'] else 0.0, axis=1)

        def calc_prov(row):
            d, v = row['days_in_stock'], row['total_value']
            if 30 <= d <= 60: return v * 0.025
            if 61 <= d <= 90: return v * 0.050
            if 91 <= d <= 120: return v * 0.075
            if d >= 121: return v * 0.100
            return 0.0
        stock['provision_value'] = stock.apply(calc_prov, axis=1)
        stock['Dealership'] = stock['location_id'].map(DEALER_MAP)
    out['stock'] = stock

    if presentation_mode:
        wip = pd.DataFrame(demo_data.get_demo_service_wip_rows())
    else:
        try:
            wip = pd.DataFrame(supabase.table("service_wip")
                                .select("location_id, estimated_value, status, created_at")
                                .execute().data)
        except Exception as e:
            st.error(f"Failed to load WIP data: {e}")
            wip = pd.DataFrame()
    if not wip.empty:
        wip['estimated_value'] = pd.to_numeric(wip['estimated_value'], errors='coerce').fillna(0.0)
        wip['Dealership'] = wip['location_id'].map(DEALER_MAP)
        wip['is_closed'] = wip['status'] == 'Invoiced / Closed'
    out['wip'] = wip

    if presentation_mode:
        deal = pd.DataFrame(demo_data.get_demo_deal_desk_rows())
    else:
        try:
            deal = pd.DataFrame(supabase.table("deal_desk")
                                 .select("location_id, retail_price, fi_vaps_revenue, net_retained_profit")
                                 .execute().data)
        except Exception as e:
            st.error(f"Failed to load deal desk data: {e}")
            deal = pd.DataFrame()
    if not deal.empty:
        for c in ['retail_price', 'fi_vaps_revenue', 'net_retained_profit']:
            deal[c] = pd.to_numeric(deal[c], errors='coerce').fillna(0.0)
        deal['Dealership'] = deal['location_id'].map(DEALER_MAP)
    out['deal'] = deal

    if presentation_mode:
        otc = pd.DataFrame(demo_data.get_demo_parts_otc_rows())
    else:
        try:
            otc = pd.DataFrame(supabase.table("parts_otc")
                                .select("location_id, retail_price, net_profit")
                                .execute().data)
        except Exception as e:
            st.error(f"Failed to load parts OTC data: {e}")
            otc = pd.DataFrame()
    if not otc.empty:
        for c in ['retail_price', 'net_profit']:
            otc[c] = pd.to_numeric(otc[c], errors='coerce').fillna(0.0)
        otc['Dealership'] = otc['location_id'].map(DEALER_MAP)
    out['otc'] = otc

    if presentation_mode:
        doc = pd.DataFrame(demo_data.get_demo_doc_expenses_rows())
    else:
        try:
            doc = pd.DataFrame(supabase.table("doc_expenses").select("location_id, amount").execute().data)
        except Exception as e:
            st.error(f"Failed to load DOC overheads data: {e}")
            doc = pd.DataFrame()
    if not doc.empty:
        doc['amount'] = pd.to_numeric(doc['amount'], errors='coerce').fillna(0.0)
        doc['Dealership'] = doc['location_id'].map(DEALER_MAP)
    out['doc'] = doc

    return out


# ====================================================================
# TOP BAR — brand row, title, live "as at" timestamp. The mockup's date
# range / filter control has no functional backend in this app (no
# rollup query is date-scoped anywhere) so it's rendered as a clearly
# inert reference control rather than a fake-working filter.
# ====================================================================
def _render_top_bar(presentation_mode):
    logos = [
        (BMW_LOGO, "BMW"), (MINI_LOGO, "MINI"), (MG_LOGO, "MG"),
    ]
    text_badges = ["🏍️ MOTORRAD", "HONDA", "JAC"]

    c1, c2, c3 = st.columns([3, 5, 3])
    with c1:
        badge_html = "".join(
            f'<img src="{src}" height="26" style="margin-right:10px;vertical-align:middle;border-radius:4px;background:#fff;padding:2px 6px;">'
            for src, _ in logos
        )
        badge_html += "".join(
            f'<span style="font-size:0.7rem;font-weight:700;letter-spacing:0.5px;margin-right:10px;'
            f'padding:4px 8px;border-radius:4px;background:var(--pv-glass);border:1px solid var(--pv-glass-border);">{t}</span>'
            for t in text_badges
        )
        st.markdown(badge_html, unsafe_allow_html=True)
    with c2:
        st.markdown(
            "<h3 style='text-align:center;margin:0;'>👑 PHASE V EXECUTIVE COMMAND CENTER</h3>",
            unsafe_allow_html=True,
        )
    with c3:
        demo_badge = (
            '<span style="font-size:0.62rem;font-weight:700;letter-spacing:0.5px;'
            'padding:2px 7px;border-radius:4px;background:rgba(241,196,15,0.18);'
            'border:1px solid rgba(241,196,15,0.5);color:#F1C40F;margin-right:8px;">DEMO</span>'
            if presentation_mode else ""
        )
        st.markdown(
            f"<div style='text-align:right;'>"
            f"<span style='font-size:0.7rem;color:var(--pv-text-dim);text-transform:uppercase;'>Data as at</span><br>"
            f"{demo_badge}<b>{datetime.now(SAST).strftime('%d %b %Y, %H:%M')}</b> &nbsp; "
            f"<span style='opacity:0.5;'>📅 Filters</span></div>",
            unsafe_allow_html=True,
        )
    st.markdown("---")


# ====================================================================
# SALES PODIUMS — top-3 branches per stream, rendered as 2nd-1st-3rd
# ranked bars. Vehicle = deal_desk retail value, Parts = parts_otc
# retail value, Service = invoiced/closed service_wip value.
# ====================================================================
def _branch_totals(df, value_col, extra_filter=None):
    if df.empty or 'Dealership' not in df.columns:
        return {d: 0.0 for d in TARGET_DEALERS}
    scoped = df[extra_filter(df)] if extra_filter else df
    grp = scoped.groupby('Dealership')[value_col].sum()
    return {d: float(grp.get(d, 0.0)) for d in TARGET_DEALERS}


def _podium_html(title, icon, totals):
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:3]
    while len(ranked) < 3:
        ranked.append(("—", 0.0))
    order = [ranked[1], ranked[0], ranked[2]]  # 2nd, 1st, 3rd visual order
    ranks = [2, 1, 3]
    heights = [55, 95, 38]

    # Fixed-width flex columns (flex-shrink:0, no wrap) so the 3 bars always
    # render as a rigid podium grid regardless of branch-name length or
    # container width -- never collapse/wrap into a stacked column.
    bars = ""
    for (name, val), rank, h in zip(order, ranks, heights):
        color = PODIUM_RANK_COLORS[rank]
        bars += f"""
        <div style="display:flex;flex-direction:column;align-items:center;justify-content:flex-end;
                    flex:0 0 33.33%;max-width:33.33%;box-sizing:border-box;height:160px;flex-shrink:0;">
            <div style="font-size:0.72rem;font-weight:600;margin-bottom:4px;text-align:center;
                        white-space:nowrap;overflow:hidden;text-overflow:ellipsis;width:100%;">{name}</div>
            <div style="font-size:0.68rem;color:var(--pv-text-dim);margin-bottom:6px;white-space:nowrap;">{fmt_currency(val, 0)}</div>
            <div style="width:64px;max-width:80%;height:{h}px;flex-shrink:0;background:linear-gradient(180deg,{color}33,{color});
                        border-top:3px solid {color};border-radius:6px 6px 0 0;box-sizing:border-box;
                        display:flex;align-items:flex-start;justify-content:center;padding-top:4px;">
                <span style="font-weight:800;color:#0b0f19;">{rank}</span>
            </div>
        </div>"""

    st.markdown(f"""
    <div style="background:var(--pv-card-bg);border:1px solid var(--pv-card-border);border-radius:14px;
                padding:14px;backdrop-filter:blur(16px);box-sizing:border-box;">
        <div style="font-weight:700;letter-spacing:0.5px;margin-bottom:10px;white-space:nowrap;">{icon} {title}</div>
        <div style="display:flex;flex-wrap:nowrap;align-items:flex-end;justify-content:space-between;gap:4px;width:100%;">{bars}</div>
    </div>
    """, unsafe_allow_html=True)


def _render_sales_podiums(data):
    p1, p2, p3 = st.columns(3)
    with p1:
        _podium_html("VEHICLE SALES", "🚗", _branch_totals(data['deal'], 'retail_price'))
    with p2:
        _podium_html("PARTS SALES", "⚙️", _branch_totals(data['otc'], 'retail_price'))
    with p3:
        _podium_html("SERVICE SALES", "🔧", _branch_totals(
            data['wip'], 'estimated_value', extra_filter=lambda d: d['is_closed']
        ))


# ====================================================================
# KEY METRICS (MTD) + IDEA BOARD
# RO Margin / CSI Score / Idea Board have no backing table in this
# schema — rendered as clearly tagged placeholders, never as fabricated
# real-looking figures, per the "strictly a mock up" instruction.
# ====================================================================
def _render_key_metrics_and_idea_board(data):
    col_metrics, col_idea = st.columns([2, 1])

    with col_metrics:
        st.markdown("##### 🔑 KEY METRICS (MTD)")
        total_revenue = (
            data['deal']['retail_price'].sum() if not data['deal'].empty else 0.0
        ) + (
            data['otc']['retail_price'].sum() if not data['otc'].empty else 0.0
        ) + (
            data['wip'][data['wip']['is_closed']]['estimated_value'].sum() if not data['wip'].empty else 0.0
        )
        gross_profit = (
            data['deal']['net_retained_profit'].sum() if not data['deal'].empty else 0.0
        ) + (
            data['otc']['net_profit'].sum() if not data['otc'].empty else 0.0
        )
        gp_pct = (gross_profit / total_revenue * 100) if total_revenue else 0.0
        units_sold = len(data['deal']) if not data['deal'].empty else 0

        m1, m2 = st.columns(2)
        m1.metric("Total Revenue", fmt_currency(total_revenue, 0))
        m2.metric("Gross Profit", fmt_currency(gross_profit, 0))
        m3, m4 = st.columns(2)
        m3.metric("Gross Profit %", f"{gp_pct:.1f}%")
        m4.metric("Units Sold", f"{units_sold}")
        m5, m6 = st.columns(2)
        m5.metric("RO Margin", "N/A", help="No backing column in this schema — placeholder.")
        m6.metric("CSI Score", "N/A", help="No backing column in this schema — placeholder.")

    with col_idea:
        st.markdown("##### 💡 IDEA BOARD")
        st.caption("Sample layout — no live data source yet.")
        for label in ["Reduce 90+ day stock provisions", "Parts counter upsell script", "Loaner fleet refresh"]:
            st.markdown(
                f"<div style='background:var(--pv-glass);border:1px solid var(--pv-glass-border);"
                f"border-radius:8px;padding:8px 10px;margin-bottom:6px;font-size:0.8rem;'>📋 {label}</div>",
                unsafe_allow_html=True,
            )


# ====================================================================
# DOC GAUGE · STOCK AGEING DONUT (by unit count) · DAILY WIP
# ====================================================================
def _doc_gauge_fig(pct):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(pct, 1),
        number={'suffix': "%", 'font': {'color': '#e8ecf4'}},
        gauge={
            'axis': {'range': [0, 100], 'tickcolor': '#8993a8'},
            'bar': {'color': '#00e0ff'},
            'bgcolor': 'rgba(0,0,0,0)',
            'steps': [
                {'range': [0, 65], 'color': 'rgba(46,204,113,0.25)'},
                {'range': [65, 100], 'color': 'rgba(231,76,60,0.25)'},
            ],
            'threshold': {'line': {'color': '#FF3366', 'width': 3}, 'thickness': 0.8, 'value': 65},
        },
    ))
    fig.update_layout(
        height=220, margin=dict(t=10, b=0, l=20, r=20),
        paper_bgcolor='rgba(0,0,0,0)', font_color='#e8ecf4',
    )
    return fig


def _stock_ageing_donut_fig(stock_df):
    bucket_order = ["0-30", "31-60", "61-90", "91-120", "120+"]
    colors = ["#2ECC71", "#F1C40F", "#E67E22", "#E74C3C", "#8E44AD"]

    def bucket(d):
        if d <= 30: return bucket_order[0]
        if d <= 60: return bucket_order[1]
        if d <= 90: return bucket_order[2]
        if d <= 120: return bucket_order[3]
        return bucket_order[4]

    if stock_df.empty:
        counts = pd.Series([0] * 5, index=bucket_order)
    else:
        counts = stock_df['days_in_stock'].apply(bucket).value_counts().reindex(bucket_order).fillna(0)

    total_units = int(counts.sum())
    fig = px.pie(
        names=bucket_order, values=counts.values, hole=0.55,
        color=bucket_order, color_discrete_sequence=colors,
    )
    fig.update_traces(textinfo='percent', hovertemplate="%{label} Days<br>%{value:.0f} units<extra></extra>")
    fig.update_layout(
        height=260, margin=dict(t=10, b=0, l=0, r=0),
        paper_bgcolor='rgba(0,0,0,0)', font_color='#e8ecf4',
        showlegend=True, legend=dict(orientation='h', y=-0.1, bgcolor='rgba(0,0,0,0)'),
        annotations=[dict(text=f"{total_units}<br>Total Units", x=0.5, y=0.5, showarrow=False, font_size=14)],
    )
    return fig


def _render_doc_stock_wip_row(data, presentation_mode):
    c1, c2, c3 = st.columns(3)

    with c1:
        st.markdown("##### ⛽ DOC RATIO")
        branch_profit = (
            (data['deal']['net_retained_profit'].sum() if not data['deal'].empty else 0.0)
            + (data['otc']['net_profit'].sum() if not data['otc'].empty else 0.0)
        )
        doc_total = data['doc']['amount'].sum() if not data['doc'].empty else 0.0
        doc_pct = (doc_total / branch_profit * 100) if branch_profit else 0.0
        st.plotly_chart(_doc_gauge_fig(doc_pct), use_container_width=True)
        st.caption("Target < 65% of gross profit")

    with c2:
        st.markdown("##### 📦 STOCK AGEING (UNITS)")
        st.plotly_chart(_stock_ageing_donut_fig(data['stock']), use_container_width=True)

    with c3:
        st.markdown("##### 🛠️ DAILY WIP")
        wip = data['wip']
        open_wip = wip[~wip['is_closed']] if not wip.empty else pd.DataFrame()
        n_open = len(open_wip)
        v_open = open_wip['estimated_value'].sum() if not open_wip.empty else 0.0
        avg_wip = (v_open / n_open) if n_open else 0.0

        if not wip.empty:
            today_str = datetime.now(SAST).strftime('%Y-%m-%d')
            opened_today = (pd.to_datetime(wip['created_at'], errors='coerce')
                             .dt.strftime('%Y-%m-%d') == today_str).sum()
        else:
            opened_today = 0

        st.metric("Open ROs", f"{n_open}")
        st.metric("Total WIP Value", fmt_currency(v_open, 0))
        st.metric("Avg WIP per RO", fmt_currency(avg_wip, 0))
        st.metric("ROs Opened Today", f"{opened_today}")
        if presentation_mode:
            st.metric("ROs Closed Today", f"{demo_data.ROS_CLOSED_TODAY}")
        else:
            st.metric("ROs Closed Today", "N/A", help="No closed_at timestamp tracked in this schema — placeholder.")


# ====================================================================
# DIVISION & DEPARTMENT PERFORMANCE — no KPI-target backend exists for
# this matrix anywhere in the schema, so it's a clearly-tagged sample
# layout (matching the mockup's dot-status UI pattern) rather than
# fabricated real-looking status data.
# ====================================================================
def _render_division_department_matrix(presentation_mode):
    st.markdown("##### 🧭 DIVISION & DEPARTMENT PERFORMANCE")
    st.caption("Sample layout — pending a KPI-target backend. Not live data.")

    dot = {"green": "#2ECC71", "amber": "#F1C40F", "red": "#E74C3C"}
    sample_rows = demo_data.DIVISION_MATRIX if presentation_mode else [
        ("BMW Sandton", ["green", "green", "amber", "green"]),
        ("BMW Bedfordview", ["amber", "green", "green", "red"]),
        ("BMW East Rand", ["green", "amber", "amber", "green"]),
        ("BMW Dalpark", ["red", "amber", "green", "amber"]),
        ("MF Sandton", ["green", "green", "green", "green"]),
        ("MF Fourways", ["amber", "red", "amber", "green"]),
    ]
    cols = ["Division", "New Sales", "Used Sales", "Service", "Parts"]

    # table-layout:fixed + an explicit colgroup locks every column to a fixed
    # width regardless of branch-name length, so the colored dots line up in
    # a perfect grid across all rows -- the actual content can never push a
    # column wider than its neighbours.
    colgroup_html = (
        "<colgroup>"
        "<col style='width:40%;'>"
        "<col style='width:15%;'><col style='width:15%;'><col style='width:15%;'><col style='width:15%;'>"
        "</colgroup>"
    )

    rows_html = ""
    for name, statuses in sample_rows:
        cells = "".join(
            f'<td style="text-align:center;width:15%;box-sizing:border-box;">'
            f'<span style="display:inline-block;width:12px;height:12px;'
            f'border-radius:50%;background:{dot[s]};"></span></td>'
            for s in statuses
        )
        rows_html += (
            f'<tr><td style="width:40%;box-sizing:border-box;white-space:nowrap;'
            f'overflow:hidden;text-overflow:ellipsis;">{name}</td>{cells}</tr>'
        )

    header_html = "".join(
        f'<th style="width:40%;box-sizing:border-box;" >{c}</th>' if i == 0
        else f'<th style="width:15%;text-align:center;box-sizing:border-box;">{c}</th>'
        for i, c in enumerate(cols)
    )
    st.markdown(
        f"<table style='width:100%;table-layout:fixed;'>{colgroup_html}<tr>{header_html}</tr>{rows_html}</table>",
        unsafe_allow_html=True,
    )


# ====================================================================
# LEGACY DETAIL ROLLUPS & DRILL-DOWN — fully preserved, real-data
# functionality from the previous Command Center build. Tucked into a
# collapsed section beneath the new mockup-aligned dashboard so no
# existing capability is lost in the rebuild.
# ====================================================================
def _render_legacy_detail(data, presentation_mode):
    df, wip_df, deal_df, otc_df, doc_df = data['stock'], data['wip'], data['deal'], data['otc'], data['doc']

    summary_data = []
    for dealer in TARGET_DEALERS:
        if not df.empty and 'Dealership' in df.columns:
            d_df = df[df['Dealership'] == dealer]
            t_stock, t_unenc, t_prov = d_df['total_value'].sum(), d_df['unencumbered_value'].sum(), d_df['provision_value'].sum()
        else:
            t_stock = t_unenc = t_prov = 0.0
        summary_data.append({'': dealer, 'Total Stock Values': t_stock, 'Total Unencumbered': t_unenc, 'Total Aging Provision': t_prov})
    summary_df = pd.DataFrame(summary_data)
    summary_df = pd.concat([summary_df, pd.DataFrame([{
        '': 'GRAND TOTAL',
        'Total Stock Values': summary_df['Total Stock Values'].sum(),
        'Total Unencumbered': summary_df['Total Unencumbered'].sum(),
        'Total Aging Provision': summary_df['Total Aging Provision'].sum(),
    }])], ignore_index=True)
    for col in ['Total Stock Values', 'Total Unencumbered', 'Total Aging Provision']:
        summary_df[col] = summary_df[col].apply(fmt_currency)

    st.markdown("### 🏢 EXECUTIVE DEALERSHIP ROLLUP")
    st.dataframe(summary_df, hide_index=True, use_container_width=True)
    st.markdown("---")

    wip_summary_data = []
    for dealer in TARGET_DEALERS:
        if not wip_df.empty and 'Dealership' in wip_df.columns:
            d_wip = wip_df[(wip_df['Dealership'] == dealer) & (~wip_df['is_closed'])]
            t_wips, t_wip_val = len(d_wip), d_wip['estimated_value'].sum()
        else:
            t_wips, t_wip_val = 0, 0.0
        wip_summary_data.append({'': dealer, 'Open WIPs': t_wips, 'Open WIPs Value': t_wip_val})
    wip_summary_df = pd.DataFrame(wip_summary_data)
    wip_summary_df = pd.concat([wip_summary_df, pd.DataFrame([{
        '': 'GRAND TOTAL',
        'Open WIPs': wip_summary_df['Open WIPs'].sum(),
        'Open WIPs Value': wip_summary_df['Open WIPs Value'].sum(),
    }])], ignore_index=True)
    wip_summary_df['Open WIPs'] = wip_summary_df['Open WIPs'].apply(lambda x: f"{x:,.0f}")
    wip_summary_df['Open WIPs Value'] = wip_summary_df['Open WIPs Value'].apply(fmt_currency)

    st.markdown("### 🔧 EXECUTIVE WORKSHOP ROLLUP")
    st.dataframe(wip_summary_df, hide_index=True, use_container_width=True)
    st.markdown("---")

    gp_summary_data = []
    for dealer in TARGET_DEALERS:
        if not deal_df.empty and 'Dealership' in deal_df.columns:
            d_deal = deal_df[deal_df['Dealership'] == dealer]
            t_units, t_vaps, t_vehicle_profit = len(d_deal), d_deal['fi_vaps_revenue'].sum(), d_deal['net_retained_profit'].sum()
        else:
            t_units, t_vaps, t_vehicle_profit = 0, 0.0, 0.0
        t_otc_profit = otc_df[otc_df['Dealership'] == dealer]['net_profit'].sum() if not otc_df.empty and 'Dealership' in otc_df.columns else 0.0
        t_doc = doc_df[doc_df['Dealership'] == dealer]['amount'].sum() if not doc_df.empty and 'Dealership' in doc_df.columns else 0.0
        t_branch_profit = t_vehicle_profit + t_otc_profit
        gp_summary_data.append({
            '': dealer, 'Locked Units': t_units, 'Total VAPS & F&I': t_vaps,
            'Vehicle Net Profit': t_vehicle_profit, 'Parts OTC Net Profit': t_otc_profit,
            'Total Branch Net Profit': t_branch_profit, 'Total DOC': t_doc, 'True Net Profit': t_branch_profit - t_doc,
        })
    gp_summary_df = pd.DataFrame(gp_summary_data)
    chart_df = gp_summary_df.rename(columns={'': 'Dealership'}).copy()
    gp_summary_df = pd.concat([gp_summary_df, pd.DataFrame([{
        '': 'GRAND TOTAL',
        'Locked Units': gp_summary_df['Locked Units'].sum(),
        'Total VAPS & F&I': gp_summary_df['Total VAPS & F&I'].sum(),
        'Vehicle Net Profit': gp_summary_df['Vehicle Net Profit'].sum(),
        'Parts OTC Net Profit': gp_summary_df['Parts OTC Net Profit'].sum(),
        'Total Branch Net Profit': gp_summary_df['Total Branch Net Profit'].sum(),
        'Total DOC': gp_summary_df['Total DOC'].sum(),
        'True Net Profit': gp_summary_df['True Net Profit'].sum(),
    }])], ignore_index=True)
    gp_summary_df['Locked Units'] = gp_summary_df['Locked Units'].apply(lambda x: f"{x:,.0f}")
    for col in ['Total VAPS & F&I', 'Vehicle Net Profit', 'Parts OTC Net Profit', 'Total Branch Net Profit', 'Total DOC', 'True Net Profit']:
        gp_summary_df[col] = gp_summary_df[col].apply(fmt_currency)

    st.markdown("### 📊 ENTERPRISE PERFORMANCE LEADERBOARD")
    if chart_df.empty or chart_df[['True Net Profit', 'Total Branch Net Profit', 'Total DOC']].abs().sum().sum() == 0:
        st.info("No profitability data logged across the enterprise yet.")
    else:
        lb1, lb2 = st.columns(2)
        with lb1:
            leaderboard_df = chart_df.sort_values('True Net Profit', ascending=False).copy()
            leaderboard_df['Result'] = leaderboard_df['True Net Profit'].apply(lambda x: 'Profit' if x >= 0 else 'Loss')
            fig_leaderboard = px.bar(
                leaderboard_df, x='Dealership', y='True Net Profit', color='Result',
                color_discrete_map={'Profit': '#2ECC71', 'Loss': '#E74C3C'},
                category_orders={'Dealership': leaderboard_df['Dealership'].tolist()},
                title="True Net Profit Leaderboard", text='True Net Profit',
            )
            fig_leaderboard.update_traces(texttemplate='R %{text:,.0f}', textposition='outside')
            fig_leaderboard.update_layout(
                showlegend=False, yaxis_title="True Net Profit (ZAR)", xaxis_title="",
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font_color='#e8ecf4', font_family='Roboto Mono, monospace',
            )
            st.plotly_chart(fig_leaderboard, use_container_width=True)
        with lb2:
            yield_vs_doc_df = chart_df.melt(id_vars='Dealership', value_vars=['Total Branch Net Profit', 'Total DOC'],
                                             var_name='Metric', value_name='Value (ZAR)')
            fig_yield_doc = px.bar(
                yield_vs_doc_df, x='Dealership', y='Value (ZAR)', color='Metric', barmode='group',
                color_discrete_map={'Total Branch Net Profit': '#3498DB', 'Total DOC': '#E67E22'},
                category_orders={'Dealership': chart_df['Dealership'].tolist()},
                title="Gross Yield vs. Overhead",
            )
            fig_yield_doc.update_layout(
                yaxis_title="Value (ZAR)", xaxis_title="", legend_title_text="",
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font_color='#e8ecf4', font_family='Roboto Mono, monospace',
            )
            st.plotly_chart(fig_yield_doc, use_container_width=True)
    st.markdown("---")

    st.markdown("### 💰 EXECUTIVE GROSS PROFIT ROLLUP")
    st.dataframe(gp_summary_df, hide_index=True, use_container_width=True)
    st.markdown("---")

    st.markdown("### 🔍 DEALERSHIP DEEP-DIVE")
    selected = st.selectbox("Drill down into specific dealership:", ["None"] + TARGET_DEALERS)
    if selected == "None":
        return

    st.markdown(f"#### 🚗 STOCK EXPOSURE: {selected}")
    if df.empty or len(df[df['Dealership'] == selected]) == 0:
        st.info(f"No active inventory logged for {selected} yet.")
    else:
        s_df = df[df['Dealership'] == selected].copy()
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Units", len(s_df))
        c2.metric("Unencumbered Units", len(s_df[s_df['is_unencumbered']]))
        c3.metric("Avg Days on Floor", f"{int(s_df['days_in_stock'].mean()) if not s_df.empty else 0} Days")

        st.markdown("##### ⚠️ High Exposure Vehicles (90+ Days)")
        exposure_df = s_df[s_df['days_in_stock'] >= 90].sort_values('days_in_stock', ascending=False)
        if exposure_df.empty:
            st.success("No critical aging stock (90+ days).")
        else:
            exp_display = exposure_df[['days_in_stock', 'total_value', 'provision_value']].copy()
            exp_display['total_value'] = exp_display['total_value'].apply(fmt_currency)
            exp_display['provision_value'] = exp_display['provision_value'].apply(fmt_currency)
            exp_display.rename(columns={'days_in_stock': 'Days on Floor', 'total_value': 'Capital Value', 'provision_value': 'Required Provision'}, inplace=True)
            st.dataframe(exp_display, hide_index=True, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"#### 🔧 WORKSHOP WIP: {selected}")
    d_wip_all = wip_df[(wip_df['Dealership'] == selected) & (~wip_df['is_closed'])] if not wip_df.empty else pd.DataFrame()
    if d_wip_all.empty:
        st.info(f"No active WIPs logged for {selected} yet.")
    else:
        wc1, wc2 = st.columns(2)
        wc1.metric("Total Open WIPs", len(d_wip_all))
        wc2.metric("Total Open WIPs Value", fmt_currency(d_wip_all['estimated_value'].sum()))

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"#### 💰 GROSS PROFIT: {selected}")
    has_deals = not deal_df.empty and len(deal_df[deal_df['Dealership'] == selected]) > 0
    has_otc = not otc_df.empty and len(otc_df[otc_df['Dealership'] == selected]) > 0
    has_doc = not doc_df.empty and len(doc_df[doc_df['Dealership'] == selected]) > 0
    if not has_deals and not has_otc and not has_doc:
        st.info(f"No locked deals, OTC parts sales, or overheads logged for {selected} yet.")
    else:
        d_deal = deal_df[deal_df['Dealership'] == selected].copy() if has_deals else pd.DataFrame(columns=['fi_vaps_revenue', 'net_retained_profit'])
        d_otc = otc_df[otc_df['Dealership'] == selected].copy() if has_otc else pd.DataFrame(columns=['net_profit'])
        d_doc = doc_df[doc_df['Dealership'] == selected].copy() if has_doc else pd.DataFrame(columns=['amount'])
        t_vehicle_profit = d_deal['net_retained_profit'].sum() if has_deals else 0.0
        t_otc_profit = d_otc['net_profit'].sum() if has_otc else 0.0
        t_doc = d_doc['amount'].sum() if has_doc else 0.0
        t_branch_profit = t_vehicle_profit + t_otc_profit

        fc1, fc2, fc3 = st.columns(3)
        fc1.metric("Locked Units", len(d_deal))
        fc2.metric("Total VAPS & F&I", fmt_currency(d_deal['fi_vaps_revenue'].sum() if has_deals else 0.0))
        fc3.metric("Total Branch Net Profit", fmt_currency(t_branch_profit))
        fc4, fc5, fc6, fc7 = st.columns(4)
        fc4.metric("Vehicle Net Profit", fmt_currency(t_vehicle_profit))
        fc5.metric("Parts OTC Net Profit", fmt_currency(t_otc_profit))
        fc6.metric("Total DOC", fmt_currency(t_doc))
        fc7.metric("True Net Profit", fmt_currency(t_branch_profit - t_doc))

    if presentation_mode:
        _render_granular_ledgers(selected)


def _render_granular_ledgers(selected):
    """Per-transaction drill-down ledgers (Vehicle Sales / Stockbook / WIP) for
    the selected dealership -- VIN/RO-level detail behind the rollup tiles
    above, so an Exco question like "which units?" has a flawless answer
    without leaving the Command Center."""
    loc_id = demo_data.LOCATION_IDS.get(selected)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"#### 📋 GRANULAR LEDGERS: {selected}")

    sales_rows = [r for r in demo_data.get_demo_vehicle_sales() if r['location_id'] == loc_id]
    with st.expander(f"🚗 Vehicle Sales Ledger ({len(sales_rows)} units)"):
        if sales_rows:
            ledger = pd.DataFrame(sales_rows)[['vin', 'vehicle_desc', 'client_name', 'sales_exec', 'retail_price', 'net_retained_profit']]
            ledger.columns = ['VIN', 'Vehicle', 'Client', 'Sales Exec', 'Retail Price', 'Net Profit']
            ledger['Retail Price'] = ledger['Retail Price'].apply(fmt_currency)
            ledger['Net Profit'] = ledger['Net Profit'].apply(fmt_currency)
            st.dataframe(ledger, hide_index=True, use_container_width=True)
        else:
            st.info("No vehicle sales records for this dealership.")

    stock_rows = [r for r in demo_data.get_demo_stockbook() if r['location_id'] == loc_id]
    with st.expander(f"📦 Stockbook Ledger ({len(stock_rows)} units)"):
        if stock_rows:
            ledger = pd.DataFrame(stock_rows)[['vsb_no', 'description', 'days_in_stock', 'total_value', 'floorplan_status']]
            ledger.columns = ['VSB Number', 'Vehicle', 'Days in Stock', 'Value', 'Floorplan Status']
            ledger['Value'] = ledger['Value'].apply(fmt_currency)
            st.dataframe(ledger.sort_values('Days in Stock', ascending=False), hide_index=True, use_container_width=True)
        else:
            st.info("No stock records for this dealership.")

    wip_rows = [r for r in demo_data.get_demo_wip() if r['location_id'] == loc_id]
    with st.expander(f"🔧 WIP Ledger ({len(wip_rows)} repair orders)"):
        if wip_rows:
            ledger = pd.DataFrame(wip_rows)[['ro_number', 'client_name', 'vehicle_details', 'service_advisor', 'status', 'estimated_value']]
            ledger.columns = ['RO Number', 'Client', 'Vehicle', 'Advisor', 'Status', 'Value']
            ledger['Value'] = ledger['Value'].apply(fmt_currency)
            st.dataframe(ledger, hide_index=True, use_container_width=True)
        else:
            st.info("No repair orders for this dealership.")


# ====================================================================
# ENTRYPOINT
# ====================================================================
def render(supabase):
    presentation_mode = st.session_state.get('presentation_mode', True)
    _render_top_bar(presentation_mode)
    data = _fetch_data(supabase, presentation_mode)

    _render_sales_podiums(data)
    st.markdown("<br>", unsafe_allow_html=True)
    _render_key_metrics_and_idea_board(data)

    st.markdown("---")
    _render_doc_stock_wip_row(data, presentation_mode)

    st.markdown("---")
    _render_division_department_matrix(presentation_mode)
    st.caption("Source: Phase V Automotive BI System")

    st.markdown("---")
    with st.expander("📂 DETAILED ENTERPRISE ROLLUPS & DRILL-DOWN"):
        _render_legacy_detail(data, presentation_mode)
