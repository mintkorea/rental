import streamlit as st

# Check and initialize session state
if 'search_performed' not in st.session_state:
    st.session_state.search_performed = False

# Now your existing code will run safely
if st.session_state.search_performed:
    # (The rest of your code)
    pass
