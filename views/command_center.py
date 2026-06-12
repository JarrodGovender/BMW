import streamlit as st
import pandas as pd

def render(supabase):
    st.markdown("## 👑 PHASE V EXECUTIVE COMMAND CENTER")
    
    # 1. Fetch ALL data across the entire holding company
    try:
        data = supabase.table("used_car_stock").select("location_id, total_value, days_in_stock, floorplan_status").execute().data
        df = pd.DataFrame(data)
    except Exception as e:
        st.error(f"Failed to load portfolio data: {e}")
        return

    if df.empty:
        st.info("No data available in the enterprise database.")
        return

    # 2. Data Cleaning & Type Casting
    df['total_value'] = pd.to_numeric(df['total_value'], errors='coerce').fillna(0.0)
    df['days_in_stock'] = pd.to_numeric(df['days_in_stock'], errors='coerce').fillna(0)
    df['floorplan_status'] = df['floorplan_status'].astype(str).str.upper()

    # Define the precise provision logic based on your matrix rules
    def calculate_provision(row):
        days = row['days_in_stock']
        val = row['total_value']
        if 30 <= days <= 60:
            return val * 0.025
        elif 61 <= days <= 90:
            return val * 0.050
        elif 91 <= days <= 120:
            return val * 0.075
        elif days >= 121:
            return val * 0.100
        return 0.0

    df['provision_value'] = df.apply(calculate_provision, axis=1)
    
    # Identify Unencumbered stock (handling variations in how it might be saved)
    df['is_unencumbered'] = df['floorplan_status'].str.contains('UNENCUMBERED', na=False)
    df['unencumbered_value'] = df.apply(lambda x: x['total_value'] if x['is_unencumbered'] else 0.0, axis=1)

    # Dictionary to map database IDs to readable Dealership Names
    dealer_map = {
        'BMW_BEDFORDVIEW': 'BMW Bedfordview',
        'BMW_SANDTON': 'BMW Sandton',
        'BMW_EASTRAND': 'BMW East Rand',
        'BMW_DALPARK': 'BMW Dalpark',
        'MF_SANDTON': 'MF Sandton',
        'MF_FOURWAYS': 'MF Fourways',
        'GLOBAL_HQ': 'Phase V HQ'
    }
    
    # Map the IDs
    df['Dealership'] = df['location_id'].map(dealer_map).fillna(df['location_id'])

    # 3. Build the Executive Rollup Table (Matching your Excel screenshot)
    summary = df.groupby('Dealership').agg(
        Total_Stock_Values=('total_value', 'sum'),
        Total_Unencumbered=('unencumbered_value', 'sum'),
        Total_Aging_Provision=('provision_value', 'sum')
    ).reset_index()

    # Calculate Grand Totals
    grand_totals = pd.DataFrame([{
        'Dealership': 'GRAND TOTAL',
        'Total_Stock_Values': summary['Total_Stock_Values'].sum(),
        'Total_Unencumbered': summary['Total_Unencumbered'].sum(),
        'Total_Aging_Provision': summary['Total_Aging_Provision'].sum()
    }])

    # Append Grand Totals to the summary
    summary = pd.concat([summary, grand_totals], ignore_index=True)

    # Format the columns for display (ZAR Currency)
    display_df = summary.copy()
    display_df.rename(columns={
        'Total_Stock_Values': 'Total Stock Values',
        'Total_Unencumbered': 'Total Unencumbered',
        'Total_Aging_Provision': 'Total Aging Provision'
    }, inplace=True)

    currency_cols = ['Total Stock Values', 'Total Unencumbered', 'Total Aging Provision']
    for col in currency_cols:
        display_df[col] = display_df[col].map('R {:,.2f}'.format)

    # 4. Render the Master Table
    st.markdown("### 🏢 EXECUTIVE DEALERSHIP ROLLUP")
    st.dataframe(display_df, hide_index=True, use_container_width=True)

    st.markdown("---")

    # 5. Interactive Drill-Down by Physical Dealership
    st.markdown("### 🔍 DEALERSHIP DEEP-DIVE")
    active_dealers = [d for d in display_df['Dealership'].tolist() if d != 'GRAND TOTAL']
    selected_dealer = st.selectbox("Select a Dealership to analyze exposure:", ["None"] + sorted(active_dealers))

    if selected_dealer != "None":
        # Filter the raw data for the specific dealer
        dealer_df = df[df['Dealership'] == selected_dealer].copy()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Units", len(dealer_df))
        c2.metric("Unencumbered Units", len(dealer_df[dealer_df['is_unencumbered']]))
        c3.metric("Avg Days in Stock", f"{int(dealer_df['days_in_stock'].mean())} Days")
        
        st.markdown(f"#### {selected_dealer} - High Exposure Vehicles (90+ Days)")
        exposure_df = dealer_df[dealer_df['days_in_stock'] >= 90].sort_values('days_in_stock', ascending=False)
        
        if exposure_df.empty:
            st.success("No vehicles over 90 days in stock.")
        else:
            exp_display = exposure_df[['days_in_stock', 'total_value', 'provision_value']].copy()
            exp_display['total_value'] = exp_display['total_value'].map('R {:,.2f}'.format)
            exp_display['provision_value'] = exp_display['provision_value'].map('R {:,.2f}'.format)
            exp_display.rename(columns={'days_in_stock': 'Days on Floor', 'total_value': 'Capital Value', 'provision_value': 'Required Provision'}, inplace=True)
            st.dataframe(exp_display, hide_index=True, use_container_width=True)
