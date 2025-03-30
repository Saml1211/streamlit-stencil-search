# Main Streamlit application entry point using st.navigation.
# This script configures the app and explicitly defines the pages
# shown in the sidebar, ensuring this script itself is not listed.
# It automatically redirects to the Visio Stencil Explorer page.

import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx

# Note: We don't set page_config here because it will be set in the page that's loaded
# Each page in the pages/ directory has its own st.set_page_config() call

# Define the pages using st.Page
# The order in this list determines the order in the sidebar.
pg = st.navigation(
    [
        st.Page("pages/01_Visio_Stencil_Explorer.py", title="Visio Stencil Explorer", icon="🔍"),
        st.Page("pages/02_Temp_File_Cleaner.py", title="Temp File Cleaner", icon="🧹"),
        st.Page("pages/03_Stencil_Health.py", title="Stencil Health", icon="🧪"),
    ]
)

# You could add app-wide initialization here if necessary,
# e.g., loading config, initializing services.
# from app.core.config import load_config
# config = load_config()
# st.session_state['config'] = config

# Run the selected page
pg.run()

# No other st.write, st.title, etc., should be here.
