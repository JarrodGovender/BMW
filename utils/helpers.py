import streamlit as st


def get_role():
    """Current user's role, uppercased -- the same lookup every view repeats."""
    return str(st.session_state.get('role', '')).upper()


def get_scope():
    """(role, username, location_id, department_id, brand_id) for the active session."""
    return (
        get_role(),
        st.session_state.get('user'),
        st.session_state.get('location_id'),
        st.session_state.get('department_id'),
        st.session_state.get('brand_id'),
    )


def fmt_currency(value, decimals=2):
    """ZAR currency formatting used throughout metrics/tables (R 1,234.56)."""
    try:
        return f"R {float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return f"R {0:,.{decimals}f}"
