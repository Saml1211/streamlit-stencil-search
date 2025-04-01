# Main Streamlit application entry point using st.navigation.
# This script configures the app and explicitly defines the pages
# shown in the sidebar, ensuring this script itself is not listed.
# It automatically redirects to the Visio Stencil Explorer page.

import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx
from app.core import config, visio
from app.core.components import directory_preset_manager
from app.core.db import StencilDatabase

# Initialize the database and rebuild the FTS index if needed
@st.cache_resource
def initialize_database():
    """Initialize the database and ensure the FTS index is built"""
    # Print a clear header
    print("\n" + "="*50)
    print("INITIALIZING DATABASE")
    print("="*50)
    
    db = StencilDatabase()
    try:
        # The integrity check happens automatically during initialization
        
        # Attempt to rebuild the FTS index - this is a no-op if already built
        rebuild_result = db.rebuild_fts_index()
        if rebuild_result:
            print("FTS index initialized successfully")
        else:
            print("FTS index initialization failed - will use standard search")
            
        # Run a quick count to verify database is working
        try:
            conn = db._get_conn()
            stencil_count = conn.execute("SELECT COUNT(*) FROM stencils").fetchone()[0]
            shape_count = conn.execute("SELECT COUNT(*) FROM shapes").fetchone()[0]
            print(f"Database contains {stencil_count} stencils and {shape_count} shapes")
        except Exception as count_error:
            print(f"Error counting database records: {count_error}")
    except Exception as e:
        print(f"Error initializing database: {e}")
        import traceback
        print(traceback.format_exc())
    finally:
        db.close()
    
    print("="*50)
    print("DATABASE INITIALIZATION COMPLETE")
    print("="*50 + "\n")
    return True

# Initialize the database at startup
_ = initialize_database()

# Note: We don't set page_config here because it will be set in the page that's loaded
# Each page in the pages/ directory has its own st.set_page_config() call

# Initialize session state values needed by all pages BEFORE any UI is created
if 'last_dir' not in st.session_state:
    # Set default directory from config
    default_dir = config.get("paths.stencil_directory", "./test_data")
    st.session_state.last_dir = default_dir

# Initialize Visio integration session state
if 'visio_connected' not in st.session_state:
    st.session_state.visio_connected = False
if 'visio_documents' not in st.session_state:
    st.session_state.visio_documents = []
if 'selected_doc_index' not in st.session_state:
    st.session_state.selected_doc_index = 1
if 'selected_page_index' not in st.session_state:
    st.session_state.selected_page_index = 1
if 'browser_width' not in st.session_state:
    st.session_state.browser_width = 1200

# Define the pages using st.Page
# The order in this list determines the order in the sidebar.
pg = st.navigation(
    [
        st.Page("pages/01_Visio_Stencil_Explorer.py", title="Visio Stencil Explorer", icon="🔍"),
        st.Page("pages/02_Temp_File_Cleaner.py", title="Temp File Cleaner", icon="🧹"),
        st.Page("pages/03_Stencil_Health.py", title="Stencil Health", icon="🧪"),
    ]
)

# Run the selected page
# No UI code should come after this line
pg.run()

# Now that the page has run and set_page_config has been called, 
# we can add our own UI elements

# Inject JavaScript to track window width for responsive design
st.markdown("""
    <script>
        // Send window width to Streamlit
        function updateWidth() {
            window.parent.postMessage({
                type: "streamlit:setComponentValue",
                value: window.innerWidth
            }, "*");
        }
        
        // Update on resize
        window.addEventListener('resize', updateWidth);
        // Initial update
        updateWidth();
    </script>
""", unsafe_allow_html=True)

# The shared sidebar components are now handled by each page
# No need to add them here
