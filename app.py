# Main Streamlit application entry point using st.navigation.
# This script configures the app and explicitly defines the pages
# shown in the sidebar, ensuring this script itself is not listed.
# It automatically redirects to the Visio Stencil Explorer page.

# IMPORTANT: Import streamlit first and call set_page_config immediately
# before any other streamlit commands
import streamlit as st
import sys
import traceback
import atexit
import signal

from app.core.db import StencilDatabase

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
from app.core.preferences import UserPreferences, _DEFAULTS

# Create a user preferences instance (no longer cached as resource)
def get_user_preferences():
    # MODIFIED START: Temporarily return a UserPreferences instance that only uses defaults
    # and does not perform file I/O on init for testing purposes.
    # The UserPreferences class needs to handle file_path=None gracefully,
    # or this might need further adjustment in UserPreferences itself.
    prefs_instance = UserPreferences(file_path=None)
    prefs_instance._prefs = dict(_DEFAULTS) # Directly set to defaults, bypassing load
    return prefs_instance
    # MODIFIED END

# Set up application logging (only once)
app_logger = setup_logger(
    name="stencil_explorer",
    level=config.get("app.log_level", "info"),
    log_to_file=True,
    log_dir="logs"
)

# Initialize session state with defaults mapped from user preferences
def initialize_session_state():
    """Initialize all session state variables in a single function."""
    prefs = get_user_preferences() # Get prefs instance
    # Directory and UI state
    st.session_state.setdefault(
        'last_dir', 
        config.get("user_preferences.default_startup_directory", config.get("paths.stencil_directory", "./test_data"))
    )
    st.session_state.setdefault('show_filters', False)
    st.session_state.setdefault('browser_width', 1200)
    st.session_state.setdefault('force_rerun', False)
    st.session_state.setdefault('initial_load_complete', False)

    # Persistent user preferences mapped to session state
    st.session_state.setdefault('search_in_document', prefs.get("document_search"))
    st.session_state.setdefault('use_fts_search', prefs.get("fts")) # Renamed key for clarity
    st.session_state.setdefault('search_result_limit', prefs.get("results_per_page")) # Renamed key
    st.session_state.setdefault('pagination_enabled', prefs.get("pagination")) # Renamed key
    st.session_state.setdefault('ui_theme', prefs.get("ui_theme"))
    st.session_state.setdefault('visio_auto_refresh', prefs.get("visio_auto_refresh"))

    # Any other legacy/config-driven session state
    st.session_state.setdefault('show_metadata_columns', config.get("user_preferences.show_metadata_columns", False))
    st.session_state.setdefault('current_search_term', "")
    st.session_state.setdefault('last_search_input', "")
    st.session_state.setdefault('search_history', [])
    st.session_state.setdefault('search_results', [])

    # Visio integration
    st.session_state.setdefault('visio_connected', False)
    st.session_state.setdefault('visio_documents', [])
    st.session_state.setdefault('selected_doc_index', 1)
    st.session_state.setdefault('selected_page_index', 1)
    st.session_state.setdefault('visio_connection_type', "local")
    st.session_state.setdefault('visio_server_name', "")

    # Stencil scanning state
    st.session_state.setdefault('stencils', [])
    st.session_state.setdefault('last_scan_dir', "")
    st.session_state.setdefault('background_scan_running', False)
    st.session_state.setdefault('last_background_scan', None)
    st.session_state.setdefault('scan_progress', 0)
    st.session_state.setdefault('scan_status', "")
    st.session_state.setdefault('preview_shape', None)

    # Shape collection
    st.session_state.setdefault('shape_collection', [])
    st.session_state.setdefault('favorite_stencils', [])
    st.session_state.setdefault('show_favorites', False)

    # Filter state
    st.session_state.setdefault('filter_date_start', None)
    st.session_state.setdefault('filter_date_end', None)
    st.session_state.setdefault('filter_min_size', 0)
    st.session_state.setdefault('filter_max_size', 50 * 1024 * 1024)  # 50 MB
    st.session_state.setdefault('filter_min_shapes', 0)
    st.session_state.setdefault('filter_max_shapes', 500)
    st.session_state.setdefault('filter_min_width', 0)
    st.session_state.setdefault('filter_max_width', 0)  # 0 means no limit
    st.session_state.setdefault('filter_min_height', 0)
    st.session_state.setdefault('filter_max_height', 0)  # 0 means no limit
    st.session_state.setdefault('filter_has_properties', False)
    st.session_state.setdefault('filter_property_name', "")
    st.session_state.setdefault('filter_property_value', "")

    # Health Monitor state
    st.session_state.setdefault('health_scan_running', False)
    st.session_state.setdefault('health_data', None)
    st.session_state.setdefault('health_scan_progress', 0)

    # Temp File Cleaner state
    st.session_state.setdefault('temp_files', [])

    # Visio Control state
    st.session_state.setdefault('visio_control_active_tab', "Documents")
    st.session_state.setdefault('visio_control_new_doc_name', "New Document")
    st.session_state.setdefault('new_page_name', "New Page")
    st.session_state.setdefault('selected_shape_id', None)
    st.session_state.setdefault('shape_edit_text', "")
    st.session_state.setdefault('shape_edit_width', 1.0)
    st.session_state.setdefault('shape_edit_height', 1.0)
    st.session_state.setdefault('shape_edit_x', 4.0)
    st.session_state.setdefault('shape_edit_y', 4.0)
    st.session_state.setdefault('new_shape_type', "rectangle")
    st.session_state.setdefault('new_shape_width', 1.0)
    st.session_state.setdefault('new_shape_height', 1.0)
    st.session_state.setdefault('new_shape_x', 4.0)
    st.session_state.setdefault('new_shape_y', 4.0)
    st.session_state.setdefault('selected_shapes_for_alignment', [])
    # Add state for batch selection in explorer
    st.session_state.setdefault('selected_shapes_for_batch', {}) # Dict to store {unique_id: shape_data}

# Always initialize session state before rendering any UI
initialize_session_state()

# Import the modularized main pages (moved to modules directory)
import modules.Visio_Stencil_Explorer as explorer
import modules.Temp_File_Cleaner as cleaner
import modules.Stencil_Health as health
import modules.Visio_Control as visiocontrol

# Create a global StencilDatabase instance for app lifetime
_db_instance = None

def get_db_instance():
    global _db_instance
    if _db_instance is None:
        try:
            _db_instance = StencilDatabase()
        except Exception as e:
            st.error(f"Error initializing database: {str(e)}")
            st.text(traceback.format_exc())
            # Create a minimal fallback instance or return None
            # This allows the app to continue even if the database is inaccessible
            return None
    return _db_instance

def cleanup():
    # Cleanup function to close DB connection and perform other cleanup tasks
    global _db_instance
    if _db_instance is not None:
        try:
            print("DEBUG: app.py - Before _db_instance.close()")
            _db_instance.close()
            print("DEBUG: app.py - After _db_instance.close()")
        except Exception as e:
            print(f"Error during cleanup: {e}")

# Register cleanup to run on program exit
atexit.register(cleanup)

# Register signal handlers for graceful exit on SIGINT and SIGTERM
def signal_handler(signum, frame):
    print(f"Received signal {signum}, running cleanup...")
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Render the shared sidebar once for the entire application
# selected_directory = render_shared_sidebar(key_prefix="main_") # Temporarily commented out
selected_directory = "." # Provide a default hardcoded value
st.sidebar.warning("Sidebar rendering is temporarily disabled for testing.") # Add a note

from app.core.visio import VisioIntegration
import streamlit as st
import traceback

def handle_batch_import():
    """Import the selected shapes from session state into Visio."""
    visio_integration = VisioIntegration()
    selected_shapes = st.session_state.get('selected_shapes_for_batch', {})
    if not selected_shapes:
        st.warning("No shapes selected for batch import.")
        return
    
    # Prepare shapes list for import_multiple_shapes
    shapes_to_import = []
    for key, shape in selected_shapes.items():
        # Expect shape dict to contain 'path' (stencil path) and 'name' (shape name)
        path = shape.get('path') or shape.get('stencil_path')
        name = shape.get('name') or shape.get('shape_name')
        if path and name:
            shapes_to_import.append({'path': path, 'name': name})
        else:
            st.error(f"Shape data missing path or name for key {key}. Skipping.")
    
    if not shapes_to_import:
        st.error("No valid shapes found for import.")
        return
    
    try:
        # Use default document and page index from session state or fallback to 1
        doc_index = st.session_state.get('selected_doc_index', 1)
        page_index = st.session_state.get('selected_page_index', 1)
        successful, total = visio_integration.import_multiple_shapes(shapes_to_import, doc_index, page_index)
        st.success(f"Imported {successful} out of {total} shapes to Visio.")
    except Exception as e:
        st.error(f"Error during batch import: {str(e)}")
        st.text(traceback.format_exc())

def handle_batch_add_favorites():
    """Add selected shapes for batch to the user's favorites collection in session state."""
    selected_shapes = st.session_state.get('selected_shapes_for_batch', {})
    if not selected_shapes:
        st.warning("No shapes selected to add to favorites.")
        return
    
    favorites = st.session_state.get('favorite_stencils', [])
    # Use a set of unique ids or unique shape identifiers to avoid duplicates
    existing_ids = set()
    for fav in favorites:
        # Assuming favorite shape dicts have a unique 'id' key or similar
        if isinstance(fav, dict):
            existing_ids.add(fav.get('id') or fav.get('unique_id'))
    
    added_count = 0
    for key, shape in selected_shapes.items():
        unique_id = shape.get('id') or shape.get('unique_id') or key
        if unique_id not in existing_ids:
            favorites.append(shape)
            existing_ids.add(unique_id)
            added_count += 1
    
    st.session_state['favorite_stencils'] = favorites
    st.success(f"Added {added_count} new shape(s) to favorites.")


# Add batch actions to the sidebar
# with st.sidebar: # Temporarily commented out
#     with st.expander("Batch Actions", expanded=False):
#         st.markdown("Perform actions on all selected shapes")
# 
#         # Display number of selected items
#         selected_count = len(st.session_state.get('selected_shapes_for_batch', {}))
#         if selected_count > 0:
#             st.caption(f"{selected_count} item(s) selected")
#         else:
#             st.caption("Select shapes in results to enable actions.")
# 
#         # Disable buttons if nothing is selected
#         disable_buttons = selected_count == 0
# 
#         st.button("Batch Import to Visio", key="batch_import_btn_main", on_click=handle_batch_import, disabled=disable_buttons)
#         st.button("Add Selected to Favorites", key="batch_favorites_btn_main", on_click=handle_batch_add_favorites, disabled=disable_buttons)
#         st.button("Remove Selected from Collection", key="batch_remove_btn_main", disabled=disable_buttons) # Add on_click later
# 
#         # Placeholder for future tagging UI
#         st.text_input("Add Tags (comma-separated)", key="batch_add_tags_input_main", disabled=disable_buttons)
#         st.button("Assign Tags to Selected", key="batch_assign_tags_btn_main", disabled=disable_buttons) # Add on_click later

# Create tabbed main content
tabs = st.tabs(["🔍 Visio Stencil Explorer", "🧹 Temp File Cleaner", "🧪 Stencil Health", "🎮 Visio Control"]) # Restored

with tabs[0]:
    # Pass the selected directory to each module instead of having them render their own sidebar
    explorer.main(selected_directory=selected_directory) # Restored

with tabs[1]:
    cleaner.main(selected_directory=selected_directory) # Restored

with tabs[2]:
    health.main(selected_directory=selected_directory) # Restored

with tabs[3]:
    visiocontrol.main(selected_directory=selected_directory) # Restored

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
