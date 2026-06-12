import streamlit as st
import pandas as pd

def render(supabase):
    st.markdown("## 👑 PHASE V EXECUTIVE COMMAND CENTER")
    
    # 1. Fetch data for all dealerships
    try:
        data = supabase.table("used_car_stock").select("total_value, days_in_stock, location, floorplan_status, stock_type").execute().data
        df = pd.DataFrame(data)
    except:
        st.error("Failed to load portfolio data.")
        return

    if df.empty:
        st.info("No data available.")
        return

    # 2. Process Data for Rollups
    df['total_value'] = pd.to_numeric(df['total_value'], errors='coerce')
    df['days_in_stock'] = pd.to_numeric(df['days_in_stock'], errors='coerce')
    
    # Create the consolidated summary
    summary = df.groupby('location').agg({
        'total_value': 'sum',
        'days_in_stock': 'mean',
        'location': 'count'
    }).rename(columns={'total_value': 'Total Asset Value', 'days_in_stock': 'Avg Days', 'location': 'Units'})
    
    # Add a "Grand Total" row at the bottom
    grand_total = summary.sum()
    grand_total.name = "GRAND TOTAL"
    summary = pd.concat([summary, grand_total.to_frame().T])

    # 3. Display Executive Grid
    st.markdown("### 📊 DEALERSHIP PORTFOLIO SUMMARY")
    
    # Format currency for display
    display_summary = summary.copy()
    display_summary['Total Asset Value'] = display_summary['Total Asset Value'].map('R {:,.2f}'.format)
    display_summary['Avg Days'] = display_summary['Avg Days'].map('{:,.1f} Days'.format)
    
    st.dataframe(display_summary, use_container_width=True)

    # 4. Interactive Drill-Down
    st.markdown("---")
    selected_dealer = st.selectbox("Drill down into specific dealership:", ["None"] + df['location'].unique().tolist())
    
    if selected_dealer != "None":
        dealer_data = df[df['location'] == selected_dealer]
        st.markdown(f"### 📍 {selected_dealer} - Detailed Provisioning")
        # Reuse your previous matrix logic or detailed breakdown here
        st.dataframe(dealer_data, use_container_width=True)
