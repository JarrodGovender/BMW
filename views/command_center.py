import streamlit as st
import pandas as pd
import plotly.express as px

def render(supabase):
    st.markdown("## 👑 PHASE V EXECUTIVE COMMAND CENTER")
    
    # 1. Define the exact layout rows from your Excel sheets
    target_dealers = [
        "BMW Bedfordview",
        "BMW Sandton",
        "BMW East Rand",
        "BMW Dalpark",
        "MF Sandton",
        "MF Fourways"
    ]

    # Map database IDs to your preferred display names
    dealer_map = {
        'BMW_BEDFORDVIEW': 'BMW Bedfordview',
        'BMW_SANDTON': 'BMW Sandton',
        'BMW_EASTRAND': 'BMW East Rand',
        'BMW_DALPARK': 'BMW Dalpark',
        'MF_SANDTON': 'MF Sandton',
        'MF_FOURWAYS': 'MF Fourways'
    }

    # ==========================================
    # MODULE 1: VEHICLE STOCK ROLLUP
    # ==========================================
    try:
        data = supabase.table("used_car_stock").select("location_id, total_value, days_in_stock, floorplan_status").execute().data
        df = pd.DataFrame(data)
    except Exception as e:
        st.error(f"Failed to load portfolio data: {e}")
        df = pd.DataFrame()

    summary_data = []

    if not df.empty:
        # Clean data types
        df['total_value'] = pd.to_numeric(df['total_value'], errors='coerce').fillna(0.0)
        df['days_in_stock'] = pd.to_numeric(df['days_in_stock'], errors='coerce').fillna(0)
        df['floorplan_status'] = df['floorplan_status'].astype(str).str.upper()

        # Apply Aging Provision Logic
        def calc_prov(row):
            d = row['days_in_stock']
            v = row['total_value']
            if 30 <= d <= 60: return v * 0.025
            elif 61 <= d <= 90: return v * 0.050
            elif 91 <= d <= 120: return v * 0.075
            elif d >= 121: return v * 0.100
            return 0.0

        df['provision_value'] = df.apply(calc_prov, axis=1)
        
        # Determine Unencumbered Status
        df['is_unencumbered'] = df['floorplan_status'].str.contains('UNENCUMBERED', na=False)
        df['unencumbered_value'] = df.apply(lambda x: x['total_value'] if x['is_unencumbered'] else 0.0, axis=1)

        # Map the raw DB location_id to the exact Excel names
        df['Dealership'] = df['location_id'].map(dealer_map)

    # ==========================================
    # ENTERPRISE INVENTORY RISK (Aging Stock Donut Chart)
    # ==========================================
    st.markdown("### 📊 ENTERPRISE INVENTORY RISK")

    if df.empty:
        st.info("No active inventory logged across the enterprise yet.")
    else:
        bucket_order = ["0-30 Days (Healthy)", "31-60 Days (Watch)", "61-90 Days (Warning)", "91+ Days (High Risk)"]

        def bucket_age(d):
            if d <= 30: return bucket_order[0]
            elif d <= 60: return bucket_order[1]
            elif d <= 90: return bucket_order[2]
            else: return bucket_order[3]

        df['age_bucket'] = df['days_in_stock'].apply(bucket_age)
        risk_df = df.groupby('age_bucket')['total_value'].sum().reindex(bucket_order).fillna(0.0).reset_index()
        risk_df.columns = ['Aging Bucket', 'Capital Value']

        risk_colors = {
            "0-30 Days (Healthy)": "#2ECC71",
            "31-60 Days (Watch)": "#F1C40F",
            "61-90 Days (Warning)": "#E67E22",
            "91+ Days (High Risk)": "#E74C3C"
        }

        fig = px.pie(
            risk_df, values='Capital Value', names='Aging Bucket', hole=0.45,
            color='Aging Bucket', color_discrete_map=risk_colors
        )
        fig.update_traces(textinfo='percent+label', hovertemplate="%{label}<br>R %{value:,.2f}<extra></extra>")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Build the Grid
    for dealer in target_dealers:
        if not df.empty and 'Dealership' in df.columns:
            d_df = df[df['Dealership'] == dealer]
            t_stock = d_df['total_value'].sum()
            t_unenc = d_df['unencumbered_value'].sum()
            t_prov = d_df['provision_value'].sum()
        else:
            t_stock = t_unenc = t_prov = 0.0

        summary_data.append({
            '': dealer,
            'Total Stock Values': t_stock,
            'Total Unencumbered': t_unenc,
            'Total Aging Provision': t_prov
        })

    summary_df = pd.DataFrame(summary_data)

    # Add the Grand Total Row
    grand_total = {
        '': 'GRAND TOTAL',
        'Total Stock Values': summary_df['Total Stock Values'].sum(),
        'Total Unencumbered': summary_df['Total Unencumbered'].sum(),
        'Total Aging Provision': summary_df['Total Aging Provision'].sum()
    }
    summary_df = pd.concat([summary_df, pd.DataFrame([grand_total])], ignore_index=True)

    # Format as proper ZAR Currency
    for col in ['Total Stock Values', 'Total Unencumbered', 'Total Aging Provision']:
        summary_df[col] = summary_df[col].apply(lambda x: f"R {x:,.2f}")

    st.markdown("### 🏢 EXECUTIVE DEALERSHIP ROLLUP")
    st.dataframe(summary_df, hide_index=True, use_container_width=True)
    st.markdown("---")

    # ==========================================
    # MODULE 2: WORKSHOP WIP ROLLUP
    # ==========================================
    try:
        # Fetch only Active/Open WIPs across all dealerships
        wip_data = supabase.table("service_wip").select("location_id, estimated_value, status").neq("status", "Invoiced / Closed").execute().data
        wip_df = pd.DataFrame(wip_data)
    except Exception as e:
        st.error(f"Failed to load WIP data: {e}")
        wip_df = pd.DataFrame()

    wip_summary_data = []

    if not wip_df.empty:
        wip_df['estimated_value'] = pd.to_numeric(wip_df['estimated_value'], errors='coerce').fillna(0.0)
        wip_df['Dealership'] = wip_df['location_id'].map(dealer_map)

    # Build the WIP Grid
    for dealer in target_dealers:
        if not wip_df.empty and 'Dealership' in wip_df.columns:
            d_wip = wip_df[wip_df['Dealership'] == dealer]
            t_wips = len(d_wip)
            t_wip_val = d_wip['estimated_value'].sum()
        else:
            t_wips = 0
            t_wip_val = 0.0

        wip_summary_data.append({
            '': dealer,
            'Open WIPs': t_wips,
            'Open WIPs Value': t_wip_val
        })

    wip_summary_df = pd.DataFrame(wip_summary_data)

    # Add the Grand Total Row for WIPs
    grand_total_wip = {
        '': 'GRAND TOTAL',
        'Open WIPs': wip_summary_df['Open WIPs'].sum(),
        'Open WIPs Value': wip_summary_df['Open WIPs Value'].sum()
    }
    wip_summary_df = pd.concat([wip_summary_df, pd.DataFrame([grand_total_wip])], ignore_index=True)

    # Formatting
    wip_summary_df['Open WIPs'] = wip_summary_df['Open WIPs'].apply(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) else str(x))
    wip_summary_df['Open WIPs Value'] = wip_summary_df['Open WIPs Value'].apply(lambda x: f"R {x:,.2f}" if isinstance(x, (int, float)) else str(x))

    st.markdown("### 🔧 EXECUTIVE WORKSHOP ROLLUP")
    st.dataframe(wip_summary_df, hide_index=True, use_container_width=True)
    st.markdown("---")

    # ==========================================
    # MODULE 3: EXECUTIVE GROSS PROFIT ROLLUP
    # ==========================================
    try:
        # Fetch deal_desk globally — no branch matrix filters, this is the God Mode overview
        deal_data = supabase.table("deal_desk").select("location_id, fi_vaps_revenue, net_retained_profit").execute().data
        deal_df = pd.DataFrame(deal_data)
    except Exception as e:
        st.error(f"Failed to load profitability data: {e}")
        deal_df = pd.DataFrame()

    try:
        # Fetch parts_otc globally — same unfiltered God Mode overview as deal_desk
        otc_data = supabase.table("parts_otc").select("location_id, net_profit").execute().data
        otc_df = pd.DataFrame(otc_data)
    except Exception as e:
        st.error(f"Failed to load OTC parts data: {e}")
        otc_df = pd.DataFrame()

    try:
        # Fetch doc_expenses globally — same unfiltered God Mode overview
        doc_data = supabase.table("doc_expenses").select("location_id, amount").execute().data
        doc_df = pd.DataFrame(doc_data)
    except Exception as e:
        st.error(f"Failed to load DOC overheads data: {e}")
        doc_df = pd.DataFrame()

    gp_summary_data = []

    if not deal_df.empty:
        deal_df['fi_vaps_revenue'] = pd.to_numeric(deal_df['fi_vaps_revenue'], errors='coerce').fillna(0.0)
        deal_df['net_retained_profit'] = pd.to_numeric(deal_df['net_retained_profit'], errors='coerce').fillna(0.0)
        deal_df['Dealership'] = deal_df['location_id'].map(dealer_map)

    if not otc_df.empty:
        otc_df['net_profit'] = pd.to_numeric(otc_df['net_profit'], errors='coerce').fillna(0.0)
        otc_df['Dealership'] = otc_df['location_id'].map(dealer_map)

    if not doc_df.empty:
        doc_df['amount'] = pd.to_numeric(doc_df['amount'], errors='coerce').fillna(0.0)
        doc_df['Dealership'] = doc_df['location_id'].map(dealer_map)

    # Build the Gross Profit Grid
    for dealer in target_dealers:
        if not deal_df.empty and 'Dealership' in deal_df.columns:
            d_deal = deal_df[deal_df['Dealership'] == dealer]
            t_units = len(d_deal)
            t_vaps = d_deal['fi_vaps_revenue'].sum()
            t_vehicle_profit = d_deal['net_retained_profit'].sum()
        else:
            t_units = 0
            t_vaps = t_vehicle_profit = 0.0

        if not otc_df.empty and 'Dealership' in otc_df.columns:
            t_otc_profit = otc_df[otc_df['Dealership'] == dealer]['net_profit'].sum()
        else:
            t_otc_profit = 0.0

        if not doc_df.empty and 'Dealership' in doc_df.columns:
            t_doc = doc_df[doc_df['Dealership'] == dealer]['amount'].sum()
        else:
            t_doc = 0.0

        t_branch_profit = t_vehicle_profit + t_otc_profit

        gp_summary_data.append({
            '': dealer,
            'Locked Units': t_units,
            'Total VAPS & F&I': t_vaps,
            'Vehicle Net Profit': t_vehicle_profit,
            'Parts OTC Net Profit': t_otc_profit,
            'Total Branch Net Profit': t_branch_profit,
            'Total DOC': t_doc,
            'True Net Profit': t_branch_profit - t_doc
        })

    gp_summary_df = pd.DataFrame(gp_summary_data)

    # Snapshot the raw numeric rollup (pre-formatting, pre-Grand-Total) to power the
    # leaderboard charts below — reuses this exact aggregation instead of re-querying.
    chart_df = gp_summary_df.rename(columns={'': 'Dealership'}).copy()

    # Add the Grand Total Row for Gross Profit
    grand_total_gp = {
        '': 'GRAND TOTAL',
        'Locked Units': gp_summary_df['Locked Units'].sum(),
        'Total VAPS & F&I': gp_summary_df['Total VAPS & F&I'].sum(),
        'Vehicle Net Profit': gp_summary_df['Vehicle Net Profit'].sum(),
        'Parts OTC Net Profit': gp_summary_df['Parts OTC Net Profit'].sum(),
        'Total Branch Net Profit': gp_summary_df['Total Branch Net Profit'].sum(),
        'Total DOC': gp_summary_df['Total DOC'].sum(),
        'True Net Profit': gp_summary_df['True Net Profit'].sum()
    }
    gp_summary_df = pd.concat([gp_summary_df, pd.DataFrame([grand_total_gp])], ignore_index=True)

    # Formatting
    gp_summary_df['Locked Units'] = gp_summary_df['Locked Units'].apply(lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) else str(x))
    for col in ['Total VAPS & F&I', 'Vehicle Net Profit', 'Parts OTC Net Profit', 'Total Branch Net Profit', 'Total DOC', 'True Net Profit']:
        gp_summary_df[col] = gp_summary_df[col].apply(lambda x: f"R {x:,.2f}" if isinstance(x, (int, float)) else str(x))

    # ==========================================
    # ENTERPRISE PERFORMANCE LEADERBOARD (Charts)
    # ==========================================
    st.markdown("### 📊 ENTERPRISE PERFORMANCE LEADERBOARD")

    if chart_df.empty or chart_df[['True Net Profit', 'Total Branch Net Profit', 'Total DOC']].abs().sum().sum() == 0:
        st.info("No profitability data logged across the enterprise yet — charts will populate once deals, OTC sales, or overheads are recorded.")
    else:
        lb1, lb2 = st.columns(2)

        with lb1:
            leaderboard_df = chart_df.sort_values('True Net Profit', ascending=False).copy()
            leaderboard_df['Result'] = leaderboard_df['True Net Profit'].apply(lambda x: 'Profit' if x >= 0 else 'Loss')

            fig_leaderboard = px.bar(
                leaderboard_df, x='Dealership', y='True Net Profit', color='Result',
                color_discrete_map={'Profit': '#2ECC71', 'Loss': '#E74C3C'},
                category_orders={'Dealership': leaderboard_df['Dealership'].tolist()},
                title="True Net Profit Leaderboard", text='True Net Profit'
            )
            fig_leaderboard.update_traces(texttemplate='R %{text:,.0f}', textposition='outside')
            fig_leaderboard.update_layout(showlegend=False, yaxis_title="True Net Profit (ZAR)", xaxis_title="")
            st.plotly_chart(fig_leaderboard, use_container_width=True)

        with lb2:
            yield_vs_doc_df = chart_df.melt(
                id_vars='Dealership',
                value_vars=['Total Branch Net Profit', 'Total DOC'],
                var_name='Metric', value_name='Value (ZAR)'
            )

            fig_yield_doc = px.bar(
                yield_vs_doc_df, x='Dealership', y='Value (ZAR)', color='Metric', barmode='group',
                color_discrete_map={'Total Branch Net Profit': '#3498DB', 'Total DOC': '#E67E22'},
                category_orders={'Dealership': chart_df['Dealership'].tolist()},
                title="Gross Yield vs. Overhead"
            )
            fig_yield_doc.update_layout(yaxis_title="Value (ZAR)", xaxis_title="", legend_title_text="")
            st.plotly_chart(fig_yield_doc, use_container_width=True)

    st.markdown("---")

    st.markdown("### 💰 EXECUTIVE GROSS PROFIT ROLLUP")
    st.dataframe(gp_summary_df, hide_index=True, use_container_width=True)
    st.markdown("---")

    # ==========================================
    # MODULE 4: DRILL-DOWN TOOL
    # ==========================================
    st.markdown("### 🔍 DEALERSHIP DEEP-DIVE")
    selected = st.selectbox("Drill down into specific dealership:", ["None"] + target_dealers)
    
    if selected != "None":
        # --- STOCK METRICS ---
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
                exp_display['total_value'] = exp_display['total_value'].apply(lambda x: f"R {x:,.2f}")
                exp_display['provision_value'] = exp_display['provision_value'].apply(lambda x: f"R {x:,.2f}")
                exp_display.rename(columns={
                    'days_in_stock': 'Days on Floor', 
                    'total_value': 'Capital Value', 
                    'provision_value': 'Required Provision'
                }, inplace=True)
                
                st.dataframe(exp_display, hide_index=True, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- WIP METRICS ---
        st.markdown(f"#### 🔧 WORKSHOP WIP: {selected}")
        if wip_df.empty or len(wip_df[wip_df['Dealership'] == selected]) == 0:
            st.info(f"No active WIPs logged for {selected} yet.")
        else:
            d_wip = wip_df[wip_df['Dealership'] == selected].copy()
            wc1, wc2 = st.columns(2)
            wc1.metric("Total Open WIPs", len(d_wip))
            wc2.metric("Total Open WIPs Value", f"R {d_wip['estimated_value'].sum():,.2f}")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- GROSS PROFIT METRICS ---
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
            fc2.metric("Total VAPS & F&I", f"R {d_deal['fi_vaps_revenue'].sum() if has_deals else 0.0:,.2f}")
            fc3.metric("Total Branch Net Profit", f"R {t_branch_profit:,.2f}")

            fc4, fc5, fc6, fc7 = st.columns(4)
            fc4.metric("Vehicle Net Profit", f"R {t_vehicle_profit:,.2f}")
            fc5.metric("Parts OTC Net Profit", f"R {t_otc_profit:,.2f}")
            fc6.metric("Total DOC", f"R {t_doc:,.2f}")
            fc7.metric("True Net Profit", f"R {t_branch_profit - t_doc:,.2f}")
