# Main Streamlit application entry point using st.navigation.
# This script configures the app and explicitly defines the pages
# shown in the sidebar, ensuring this script itself is not listed.
# It automatically redirects to the Visio Stencil Explorer page.

# IMPORTANT: Import streamlit first and call set_page_config immediately
# before any other streamlit commands
import streamlit as st
import sys
import traceback

# Set a default page config here that must be the first Streamlit command
st.set_page_config(
    page_title="Visio Stencil Explorer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Now import other modules and continue with initialization
from streamlit.runtime.scriptrunner import get_script_run_ctx
from app.core import config, visio
from app.core.components import directory_preset_manager
from app.core.db import StencilDatabase
from app.core.custom_styles import inject_custom_css
from app.core.logging_utils import setup_logger, get_logger

# Set up application logging
app_logger = setup_logger(
    name="stencil_explorer",
    level=config.get("app.log_level", "info"),
    log_to_file=True,
    log_dir="logs"
)

# Set up exception handling
def handle_exception(exc_type, exc_value, exc_traceback):
    """Global exception handler to log unhandled exceptions"""
    if issubclass(exc_type, KeyboardInterrupt):
        # Don't log keyboard interrupt
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    app_logger.critical("Unhandled exception:", exc_info=(exc_type, exc_value, exc_traceback))

# Set the exception hook
sys.excepthook = handle_exception

# Log application startup
app_logger.info(f"Starting Visio Stencil Explorer v{config.get('app.version', '1.0.0')}")

# Initialize the database and rebuild the FTS index if needed
@st.cache_resource
def initialize_database():
    """Initialize the database and ensure the FTS index is built"""
    # Print a clear header
    app_logger.info("Initializing database")

    # Check if database file exists and is not corrupted
    db_path = config.get("paths.database", "data/stencil_cache.db")
    try:
        # Try to open the database and check integrity
        import sqlite3
        import os

        # If database doesn't exist, we'll create it normally
        if not os.path.exists(db_path):
            app_logger.info(f"Database file {db_path} does not exist, will create new database")
        else:
            # Check if database is corrupted
            try:
                test_conn = sqlite3.connect(db_path)
                integrity_result = test_conn.execute("PRAGMA integrity_check").fetchone()[0]
                test_conn.close()

                if integrity_result != "ok":
                    app_logger.error(f"Database integrity check failed: {integrity_result}")
                    # Backup and recreate database
                    backup_and_recreate_db(db_path)
            except sqlite3.OperationalError as e:
                if "database disk image is malformed" in str(e):
                    app_logger.error(f"Database corruption detected: {e}")
                    # Backup and recreate database
                    backup_and_recreate_db(db_path)
                else:
                    app_logger.error(f"SQLite error: {e}")
            except Exception as e:
                app_logger.error(f"Error checking database integrity: {e}")
    except Exception as e:
        app_logger.error(f"Error during database pre-check: {e}")

    db = StencilDatabase()
    try:
        # The integrity check happens automatically during initialization

        # Attempt to rebuild the FTS index - this is a no-op if already built
        app_logger.debug("Rebuilding FTS index if needed")
        rebuild_result = db.rebuild_fts_index()
        if rebuild_result:
            app_logger.info("FTS index initialized successfully")
        else:
            app_logger.warning("FTS index initialization failed - will use standard search")

        # Run a quick count to verify database is working
        try:
            conn = db._get_conn()
            stencil_count = conn.execute("SELECT COUNT(*) FROM stencils").fetchone()[0]
            shape_count = conn.execute("SELECT COUNT(*) FROM shapes").fetchone()[0]
            app_logger.info(f"Database contains {stencil_count} stencils and {shape_count} shapes")
        except Exception as count_error:
            app_logger.error(f"Error counting database records: {count_error}")
    except Exception as e:
        app_logger.error(f"Error initializing database: {e}")
        app_logger.error(traceback.format_exc())
    finally:
        db.close()

    app_logger.info("Database initialization complete")
    return True

def backup_and_recreate_db(db_path):
    """Backup and recreate a corrupted database"""
    import os
    import shutil
    from datetime import datetime

    try:
        # Create a backup of the corrupt database
        backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        if os.path.exists(db_path):
            shutil.copy2(db_path, backup_path)
            app_logger.info(f"Created database backup at {backup_path}")

            # Remove the corrupted database
            os.remove(db_path)
            app_logger.info(f"Removed corrupted database file {db_path}")

            # A new database will be created automatically when StencilDatabase is initialized
            app_logger.info("Database will be recreated on next access")
            return True
    except Exception as e:
        app_logger.error(f"Error backing up database: {e}")
        return False

# Initialize the database at startup
_ = initialize_database()

# Page config is already set at the top of the file
# No need to set it again here

# Initialize session state values needed by all pages BEFORE any UI is created
if 'last_dir' not in st.session_state:
    # Set default directory from user preferences
    default_dir = config.get("user_preferences.default_startup_directory", config.get("paths.stencil_directory", "./test_data"))
    st.session_state.last_dir = default_dir

# Initialize search preferences from config
if 'use_fts_search' not in st.session_state:
    st.session_state.use_fts_search = config.get("user_preferences.default_search_mode", True)
if 'search_result_limit' not in st.session_state:
    st.session_state.search_result_limit = config.get("user_preferences.default_result_limit", 1000)
if 'show_metadata_columns' not in st.session_state:
    st.session_state.show_metadata_columns = config.get("user_preferences.show_metadata_columns", False)

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
        st.Page("pages/04_Visio_Control.py", title="Visio Control", icon="🎮"),
    ]
)

# Run the selected page
# No UI code should come after this line
pg.run()

# Now that the page has run and set_page_config has been called,
# we can add our own UI elements

# Apply custom CSS styles for improved UI layout and spacing
inject_custom_css()

# Inject JavaScript to track window width for responsive design and CSS for consistent container heights
st.markdown("""
    <script>
        // Send window width to Streamlit
        function updateWidth() {
            const width = window.innerWidth;
            window.parent.postMessage({
                type: "streamlit:setComponentValue",
                value: {"browser_width": width}
            }, "*");
        }

        // Update on resize
        window.addEventListener('resize', updateWidth);
        // Initial update
        updateWidth();
    </script>

    <style>
        /* Set standard height for all containers with borders */
        [data-testid="stCaptionContainer"] > div:has(> div[data-testid="stVerticalBlock"]) > div:has(> div[data-baseweb="card"]) {
            min-height: 300px !important;
        }

        /* Make sure content scrolls if it exceeds the container height */
        [data-testid="stVerticalBlock"] > div:has(> div[data-baseweb="card"]) > div {
            max-height: 300px;
            overflow-y: auto;
        }

        /* Ensure sidebar containers have consistent height too */
        .sidebar .element-container:has(> div[data-testid="stVerticalBlock"]) > div:has(> div[data-baseweb="card"]) {
            min-height: 150px !important;
        }
    </style>
""", unsafe_allow_html=True)

# The shared sidebar components are now handled by each page
# No need to add them here
