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
from app.core.components import directory_preset_manager, render_shared_sidebar
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

# Initialize ALL session state values needed by all pages BEFORE any UI is created
def initialize_session_state():
    """Initialize all session state variables in a single function"""
    # Directory and UI state
    if 'last_dir' not in st.session_state:
        # Set default directory from user preferences
        default_dir = config.get("user_preferences.default_startup_directory", config.get("paths.stencil_directory", "./test_data"))
        st.session_state.last_dir = default_dir
    if 'show_filters' not in st.session_state:
        st.session_state.show_filters = False
    if 'browser_width' not in st.session_state:
        st.session_state.browser_width = 1200
    if 'force_rerun' not in st.session_state:
        st.session_state.force_rerun = False
    if 'initial_load_complete' not in st.session_state:
        st.session_state.initial_load_complete = False

    # Search preferences
    if 'use_fts_search' not in st.session_state:
        st.session_state.use_fts_search = config.get("user_preferences.default_search_mode", True)
    if 'search_result_limit' not in st.session_state:
        st.session_state.search_result_limit = config.get("user_preferences.default_result_limit", 1000)
    if 'show_metadata_columns' not in st.session_state:
        st.session_state.show_metadata_columns = config.get("user_preferences.show_metadata_columns", False)
    if 'current_search_term' not in st.session_state:
        st.session_state.current_search_term = ""
    if 'last_search_input' not in st.session_state:
        st.session_state.last_search_input = ""
    if 'search_history' not in st.session_state:
        st.session_state.search_history = []
    if 'search_results' not in st.session_state:
        st.session_state.search_results = []
    if 'search_in_document' not in st.session_state:
        st.session_state.search_in_document = False

    # Visio integration
    if 'visio_connected' not in st.session_state:
        st.session_state.visio_connected = False
    if 'visio_documents' not in st.session_state:
        st.session_state.visio_documents = []
    if 'selected_doc_index' not in st.session_state:
        st.session_state.selected_doc_index = 1
    if 'selected_page_index' not in st.session_state:
        st.session_state.selected_page_index = 1
    if 'visio_connection_type' not in st.session_state:
        st.session_state.visio_connection_type = "local"
    if 'visio_server_name' not in st.session_state:
        st.session_state.visio_server_name = ""

    # Stencil scanning state
    if 'stencils' not in st.session_state:
        st.session_state.stencils = []
    if 'last_scan_dir' not in st.session_state:
        st.session_state.last_scan_dir = ""
    if 'background_scan_running' not in st.session_state:
        st.session_state.background_scan_running = False
    if 'last_background_scan' not in st.session_state:
        st.session_state.last_background_scan = None
    if 'scan_progress' not in st.session_state:
        st.session_state.scan_progress = 0
    if 'scan_status' not in st.session_state:
        st.session_state.scan_status = ""
    if 'preview_shape' not in st.session_state:
        st.session_state.preview_shape = None

    # Shape collection
    if 'shape_collection' not in st.session_state:
        st.session_state.shape_collection = []
    if 'favorite_stencils' not in st.session_state:
        st.session_state.favorite_stencils = []
    if 'show_favorites' not in st.session_state:
        st.session_state.show_favorites = False

    # Filter state
    if 'filter_date_start' not in st.session_state:
        st.session_state.filter_date_start = None
    if 'filter_date_end' not in st.session_state:
        st.session_state.filter_date_end = None
    if 'filter_min_size' not in st.session_state:
        st.session_state.filter_min_size = 0
    if 'filter_max_size' not in st.session_state:
        st.session_state.filter_max_size = 50 * 1024 * 1024  # 50 MB
    if 'filter_min_shapes' not in st.session_state:
        st.session_state.filter_min_shapes = 0
    if 'filter_max_shapes' not in st.session_state:
        st.session_state.filter_max_shapes = 500
    if 'filter_min_width' not in st.session_state:
        st.session_state.filter_min_width = 0
    if 'filter_max_width' not in st.session_state:
        st.session_state.filter_max_width = 0  # 0 means no limit
    if 'filter_min_height' not in st.session_state:
        st.session_state.filter_min_height = 0
    if 'filter_max_height' not in st.session_state:
        st.session_state.filter_max_height = 0  # 0 means no limit
    if 'filter_has_properties' not in st.session_state:
        st.session_state.filter_has_properties = False
    if 'filter_property_name' not in st.session_state:
        st.session_state.filter_property_name = ""
    if 'filter_property_value' not in st.session_state:
        st.session_state.filter_property_value = ""

    # Health Monitor state
    if 'health_scan_running' not in st.session_state:
        st.session_state.health_scan_running = False
    if 'health_data' not in st.session_state:
        st.session_state.health_data = None
    if 'health_scan_progress' not in st.session_state:
        st.session_state.health_scan_progress = 0

    # Temp File Cleaner state
    if 'temp_files' not in st.session_state:
        st.session_state.temp_files = []

    # Visio Control state
    if 'visio_control_active_tab' not in st.session_state:
        st.session_state.visio_control_active_tab = "Documents"
    if 'visio_control_new_doc_name' not in st.session_state:
        st.session_state.visio_control_new_doc_name = "New Document"
    if 'new_page_name' not in st.session_state:
        st.session_state.new_page_name = "New Page"
    if 'selected_shape_id' not in st.session_state:
        st.session_state.selected_shape_id = None
    if 'shape_edit_text' not in st.session_state:
        st.session_state.shape_edit_text = ""
    if 'shape_edit_width' not in st.session_state:
        st.session_state.shape_edit_width = 1.0
    if 'shape_edit_height' not in st.session_state:
        st.session_state.shape_edit_height = 1.0
    if 'shape_edit_x' not in st.session_state:
        st.session_state.shape_edit_x = 4.0
    if 'shape_edit_y' not in st.session_state:
        st.session_state.shape_edit_y = 4.0
    if 'new_shape_type' not in st.session_state:
        st.session_state.new_shape_type = "rectangle"
    if 'new_shape_width' not in st.session_state:
        st.session_state.new_shape_width = 1.0
    if 'new_shape_height' not in st.session_state:
        st.session_state.new_shape_height = 1.0
    if 'new_shape_x' not in st.session_state:
        st.session_state.new_shape_x = 4.0
    if 'new_shape_y' not in st.session_state:
        st.session_state.new_shape_y = 4.0
    if 'selected_shapes_for_alignment' not in st.session_state:
        st.session_state.selected_shapes_for_alignment = []
    # Add state for batch selection in explorer
    if 'selected_shapes_for_batch' not in st.session_state:
        st.session_state.selected_shapes_for_batch = {} # Dict to store {unique_id: shape_data}

# Initialize all session state variables
initialize_session_state()

# Import the modularized main pages (moved to modules directory)
import modules.Visio_Stencil_Explorer as explorer
import modules.Temp_File_Cleaner as cleaner
import modules.Stencil_Health as health
import modules.Visio_Control as visiocontrol

# --- Batch Action Callbacks ---
def handle_batch_import():
    if not visio.is_connected():
        st.sidebar.error("Visio not connected.")
        return

    selected_shapes = st.session_state.get('selected_shapes_for_batch', {})
    if not selected_shapes:
        st.sidebar.warning("No shapes selected for import.")
        return

    # Prepare shapes for import (only those from stencils)
    shapes_to_import = []
    for unique_id, shape_data in selected_shapes.items():
        if not shape_data.get('is_document_shape'): # Only import shapes from stencils
            shapes_to_import.append({
                "path": shape_data.get('stencil_path'),
                "name": shape_data.get('shape_name')
            })

    if not shapes_to_import:
        st.sidebar.warning("No stencil shapes selected for import.")
        return

    doc_index = st.session_state.get('selected_doc_index', 1)
    page_index = st.session_state.get('selected_page_index', 1)

    with st.spinner(f"Importing {len(shapes_to_import)} shapes..."):
        success_count, total_count = visio.import_multiple_shapes(shapes_to_import, doc_index, page_index)

    if success_count > 0:
        st.sidebar.success(f"Imported {success_count}/{total_count} shapes.")
        # Optionally clear selection after successful import
        # st.session_state.selected_shapes_for_batch = {}
    else:
        st.sidebar.error(f"Failed to import shapes (Imported {success_count}/{total_count}).")

def handle_batch_add_favorites():
    selected_shapes = st.session_state.get('selected_shapes_for_batch', {})
    if not selected_shapes:
        st.sidebar.warning("No shapes selected to add to favorites.")
        return

    db = StencilDatabase()
    added_count = 0
    error_count = 0
    skipped_count = 0

    with st.spinner(f"Adding {len(selected_shapes)} items to favorites..."):
        for unique_id, shape_data in selected_shapes.items():
            try:
                if shape_data.get('is_document_shape'):
                    # Add document shape by ID (if shape_id exists)
                    shape_id = shape_data.get('shape_id')
                    stencil_path_for_fav = shape_data.get('stencil_path') # This is the special visio_doc_... path
                    # We need a real stencil path to link in favorites. This feature might not be fully compatible.
                    # For now, we'll skip adding live document shapes to favorites directly via batch.
                    # A better approach might be to favorite the *source* stencil/shape if identifiable.
                    # logger.warning(f"Skipping favorite for document shape ID {shape_id} - feature needs refinement.")
                    skipped_count += 1
                    continue # Skip document shapes for now
                else:
                    # Add stencil shape by path and shape_id
                    stencil_path = shape_data.get('stencil_path')
                    shape_id = shape_data.get('shape_id') # Assumes shape_id is in the dict from db search
                    if stencil_path and shape_id:
                         fav_result = db.add_favorite_shape_by_id(stencil_path, shape_id)
                         if fav_result: # Check if it returned a valid dict (meaning success or already existed)
                             added_count += 1
                         else: # Likely an error or shape not found
                             error_count += 1
                    else:
                         skipped_count += 1 # Missing data to add favorite
            except Exception as e:
                # logger.error(f"Error adding favorite for {unique_id}: {e}")
                error_count += 1
    db.close()

    if added_count > 0:
        st.sidebar.success(f"Added {added_count} shapes to favorites.")
    if error_count > 0:
        st.sidebar.error(f"Failed to add {error_count} shapes to favorites.")
    if skipped_count > 0:
        st.sidebar.warning(f"Skipped {skipped_count} items (e.g., document shapes or missing data).)")
    # Optionally clear selection
    # st.session_state.selected_shapes_for_batch = {}

# Render the shared sidebar once for the entire application
selected_directory = render_shared_sidebar(key_prefix="main_")

# Add batch actions to the sidebar
with st.sidebar:
    with st.expander("Batch Actions", expanded=False):
        st.markdown("Perform actions on all selected shapes")

        # Display number of selected items
        selected_count = len(st.session_state.get('selected_shapes_for_batch', {}))
        if selected_count > 0:
            st.caption(f"{selected_count} item(s) selected")
        else:
            st.caption("Select shapes in results to enable actions.")

        # Disable buttons if nothing is selected
        disable_buttons = selected_count == 0

        st.button("Batch Import to Visio", key="batch_import_btn_main", on_click=handle_batch_import, disabled=disable_buttons)
        st.button("Add Selected to Favorites", key="batch_favorites_btn_main", on_click=handle_batch_add_favorites, disabled=disable_buttons)
        st.button("Remove Selected from Collection", key="batch_remove_btn_main", disabled=disable_buttons) # Add on_click later

        # Placeholder for future tagging UI
        st.text_input("Add Tags (comma-separated)", key="batch_add_tags_input_main", disabled=disable_buttons)
        st.button("Assign Tags to Selected", key="batch_assign_tags_btn_main", disabled=disable_buttons) # Add on_click later

# Create tabbed main content
tabs = st.tabs(["🔍 Visio Stencil Explorer", "🧹 Temp File Cleaner", "🧪 Stencil Health", "🎮 Visio Control"])

with tabs[0]:
    # Pass the selected directory to each module instead of having them render their own sidebar
    explorer.main(selected_directory=selected_directory)

with tabs[1]:
    cleaner.main(selected_directory=selected_directory)

with tabs[2]:
    health.main(selected_directory=selected_directory)

with tabs[3]:
    visiocontrol.main(selected_directory=selected_directory)

# Now that the page has run and set_page_config has been called,
# we can add our own UI elements

# Apply critical CSS first - this will be applied immediately before any JavaScript runs
# This ensures the layout is correct from the very beginning
st.markdown("""
<style>
    /* Force immediate application of critical styles */
    body {
        opacity: 0;
        animation: fadeIn 0.5s forwards;
    }
    @keyframes fadeIn {
        to { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)

# Apply custom CSS styles for improved UI layout and spacing
inject_custom_css()
st.markdown("""
    <style>
        /* Critical CSS that needs to be applied immediately */
        /* Default container heights for different screen sizes */
        @media (min-width: 992px) {
            /* Desktop */
            [data-testid="stCaptionContainer"] div[data-baseweb="card"],
            div[data-baseweb="card"] {
                min-height: 300px !important;
                max-height: 600px !important;
            }
            .sidebar div[data-baseweb="card"] {
                min-height: 150px !important;
            }
        }

        @media (max-width: 991px) and (min-width: 768px) {
            /* Tablet */
            [data-testid="stCaptionContainer"] div[data-baseweb="card"],
            div[data-baseweb="card"] {
                min-height: 250px !important;
                max-height: 500px !important;
            }
            .sidebar div[data-baseweb="card"] {
                min-height: 120px !important;
            }
        }

        @media (max-width: 767px) {
            /* Mobile */
            [data-testid="stCaptionContainer"] div[data-baseweb="card"],
            div[data-baseweb="card"] {
                min-height: 200px !important;
                max-height: 400px !important;
            }
            .sidebar div[data-baseweb="card"] {
                min-height: 100px !important;
            }
        }

        /* Make sure content scrolls if it exceeds the container height */
        div[data-baseweb="card"] > div {
            overflow-y: auto;
        }

        /* Ensure consistent spacing */
        div[data-testid="stVerticalBlock"] > div {
            margin-bottom: 16px;
        }
    </style>
""", unsafe_allow_html=True)

# Inject JavaScript to track window width for responsive design and additional CSS
st.markdown("""
    <script>
        // Wait for Streamlit to be fully initialized
        window.addEventListener('DOMContentLoaded', (event) => {
            // Function to send window width to Streamlit
            function updateWidth() {
                const width = window.innerWidth;
                window.parent.postMessage({
                    type: "streamlit:setComponentValue",
                    value: {"browser_width": width}
                }, "*");

                // Force a rerun on first load after a delay
                if (!window.initialLoadComplete) {
                    window.initialLoadComplete = true;
                    setTimeout(() => {
                        window.parent.postMessage({
                            type: "streamlit:setComponentValue",
                            value: {"force_rerun": true}
                        }, "*");
                    }, 1000); // 1 second delay
                }
            }

            // Update on resize
            window.addEventListener('resize', updateWidth);

            // Initial update with a slight delay to ensure Streamlit is ready
            setTimeout(updateWidth, 300);
        });
    </script>
""", unsafe_allow_html=True)

# The shared sidebar components are now handled by each page
# No need to add them here

# Check if we need to force a rerun (triggered by JavaScript on first load)
if st.session_state.get('force_rerun', False) and not st.session_state.get('initial_load_complete', False):
    # Mark initial load as complete to prevent infinite reruns
    st.session_state.initial_load_complete = True
    # Force a rerun to ensure proper layout
    st.rerun()
