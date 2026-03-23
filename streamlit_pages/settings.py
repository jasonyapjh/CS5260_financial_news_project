import streamlit as st

def show():
    st.title("⚙️ Settings")
    st.markdown("""
    This is where you can configure your preferences for the Financial News Intelligence app. 
    You can customize your news digest, manage your watchlist, and set up notifications.
    **Note:** Settings will be saved for your current session. Future versions may include persistent storage.
    """)