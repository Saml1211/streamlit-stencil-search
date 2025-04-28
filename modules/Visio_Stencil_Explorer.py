import streamlit as st
import os
import sys
import time
import pandas as pd
import io
import base64
from datetime import datetime, timedelta
import threading
from typing import List, Dict, Any, Optional

# Add the parent directory to path so we can import from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Performance Enhancements ---
from app.core.utils import DebounceSearch
from app.core.preview_cache import PreviewCache

from app.core.query_parser import parse_search_query
from app.core import config
from app.core import scan_directory, parse_visio_stencil, get_shape_preview, visio, directory_preset_manager
from app.core.db import StencilDatabase
from app.core.components import render_shared_sidebar
from app.core.custom_styles import inject_spacer
from app.core.logging_utils import MemoryStreamHandler, LOG_LEVELS, get_logger

# Setup in-memory log handler for diagnostics panel
_logger_name = "visio_integration"
_mem_handler = MemoryStreamHandler(capacity=100)
_logger = get_logger(_logger_name)
if not any(isinstance(h, MemoryStreamHandler) for h in _logger.handlers):
    _logger.addHandler(_mem_handler)

def diagnostics_sidebar():
    """Render Diagnostics panel: log level, live logs, copy-to-clipboard."""
    import streamlit as st

    st.sidebar.markdown("### Diagnostics")
    log_level = st.sidebar.selectbox(
        "Log Level",
        options=list(LOG_LEVELS.keys()),
        index=list(LOG_LEVELS.keys()).index("info"),
        key="diagnostics_log_level"
    )
    # Set log level dynamically
    _logger.setLevel(LOG_LEVELS[log_level])
    for h in _logger.handlers:
        h.setLevel(LOG_LEVELS[log_level])

    logs = _mem_handler.get_latest_logs()
    log_text = "\n".join(logs)
    st.sidebar.text_area(
        "Recent Logs",
        log_text,
        height=200,
        key="diagnostics_log_text"
    )

    # JS clipboard copy hack
    copy_code = """
    <script>
    function copyToClipboard(text) {
        navigator.clipboard.writeText(text);
    }
    const btn = document.getElementById("copy-logs-btn");
    if (btn) {
        btn.onclick = function() {
            copyToClipboard(document.getElementById("log-textarea").value);
        }
    }
    </script>
    """
    st.sidebar.markdown('<textarea id="log-textarea" style="display:none;">{}</textarea>'.format(log_text), unsafe_allow_html=True)
    st.sidebar.button("Copy logs", key="copy-logs-btn")
    st.sidebar.markdown(copy_code, unsafe_allow_html=True)

# Page config is now set in app.py to avoid the 'set_page_config must be first' error
# st.set_page_config(
#     page_title=config.get("app.title", "Visio Stencil Explorer"),
#     page_icon="🔍",
#     layout="wide",
#     initial_sidebar_state="expanded",
# )

from app.core.preferences import UserPreferences

import streamlit as st

@st.cache_resource
def get_user_preferences():
    return UserPreferences()

def user_preferences_sidebar(prefs):
    """Render a sidebar UI for setting user preferences."""
    st.sidebar.markdown("### User Preferences")

    # Document Search Toggle
    doc_search = st.sidebar.checkbox(
        "Include Visio Document Shapes",
        value=prefs.get("document_search"),
        help="When enabled, search will include shapes from open Visio documents.",
        key="prefs_doc_search"
    )
    prefs.set("document_search", doc_search)

    # FTS Toggle
    fts = st.sidebar.checkbox(
        "Enable Full-Text Search (FTS)",
        value=prefs.get("fts"),
        help="Use full-text index for faster, smarter search.",
        key="prefs_fts"
    )
    prefs.set("fts", fts)

    # Results Per Page
    results_per_page = st.sidebar.number_input(
        "Results per page",
        min_value=5,
        max_value=100,
        value=prefs.get("results_per_page"),
        step=5,
        key="prefs_results_per_page"
    )
    prefs.set("results_per_page", results_per_page)

    # Pagination
    pagination = st.sidebar.checkbox(
        "Enable Pagination",
        value=prefs.get("pagination"),
        key="prefs_pagination"
    )
    prefs.set("pagination", pagination)

    # UI Theme
    ui_theme = st.sidebar.selectbox(
        "UI Theme",
        options=["default", "high_contrast"],
        index=0 if prefs.get("ui_theme") == "default" else 1,
        help="Set interface style for accessibility.",
        key="prefs_ui_theme"
    )
    prefs.set("ui_theme", ui_theme)

    # Visio Auto-Refresh
    visio_auto_refresh = st.sidebar.checkbox(
        "Auto-refresh Visio Connection",
        value=prefs.get("visio_auto_refresh"),
        help="Automatically refresh the Visio connection.",
        key="prefs_visio_auto_refresh"
    )
    prefs.set("visio_auto_refresh", visio_auto_refresh)

    # Reset to defaults
    if st.sidebar.button("Reset Preferences to Defaults"):
        prefs.reset()
        st.experimental_rerun()

    # Save (persist) preferences
    prefs.save()
# Session state is now initialized in app.py
# No need to initialize session state variables here

def background_scan(root_dir: str):
    """Background scanning function"""
    try:
        st.session_state.background_scan_running = True
        st.session_state.scan_status = "Scanning..."
        st.session_state.scan_progress = 0

        # Perform the scan with caching
        stencils = scan_directory(root_dir, parse_visio_stencil, use_cache=True)

        # Update session state
        st.session_state.stencils = stencils
        st.session_state.last_scan_dir = root_dir
        st.session_state.last_background_scan = datetime.now()
        st.session_state.scan_status = "Scan complete"
        st.session_state.scan_progress = 100
    except Exception as e:
        st.session_state.scan_status = f"Error: {str(e)}"
    finally:
        st.session_state.background_scan_running = False

def toggle_shape_preview(shape=None):
    """Toggle shape preview in session state"""
    st.session_state.preview_shape = shape

def generate_export_link(df, file_type):
    """Generate a download link for exporting search results"""
    if file_type == 'csv':
        csv = df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'data:file/csv;base64,{b64}'
        download_filename = f'stencil_search_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    elif file_type == 'excel':
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Search Results', index=False)
        b64 = base64.b64encode(output.getvalue()).decode()
        href = f'data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}'
        download_filename = f'stencil_search_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    elif file_type == 'txt':
        txt = df.to_csv(sep='\t', index=False)
        b64 = base64.b64encode(txt.encode()).decode()
        href = f'data:file/txt;base64,{b64}'
        download_filename = f'stencil_search_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'

    return f'<a href="{href}" download="{download_filename}" target="_blank">Download {file_type.upper()}</a>'

def add_to_collection(shape_name, stencil_name, stencil_path):
    """Add a shape to the collection"""
    # Check if shape already exists in collection
    for item in st.session_state.shape_collection:
        if item["name"] == shape_name and item["path"] == stencil_path:
            return False  # Already in collection

    # Add to collection
    st.session_state.shape_collection.append({
        "name": shape_name,
        "stencil_name": stencil_name,
        "path": stencil_path
    })
    return True

def remove_from_collection(index):
    """Remove a shape from the collection"""
    if 0 <= index < len(st.session_state.shape_collection):
        st.session_state.shape_collection.pop(index)
        return True
    return False

def clear_collection():
    """Clear the entire shape collection"""
    st.session_state.shape_collection = []

def refresh_visio_connection():
    """Refresh the connection to Visio and update stencil list"""
    # Attempt to connect to Visio
    connected = visio.connect()
    st.session_state.visio_connected = connected

    # Get list of open stencils
    if connected:
        st.session_state.visio_documents = visio.get_open_documents()

        # Get default stencil and page if available
        doc_index, page_index, found_valid = visio.get_default_document_page()
        if found_valid:
            st.session_state.selected_doc_index = doc_index
            st.session_state.selected_page_index = page_index
        else:
            # Reset selected stencil/page if none available
            st.session_state.selected_doc_index = 1
            st.session_state.selected_page_index = 1
    else:
        st.session_state.visio_documents = []

def import_collection_to_visio(doc_index, page_index):
    """Import the collected shapes to Visio"""
    if not st.session_state.visio_connected:
        return False, "Not connected to Visio. Please refresh connection."

    if not st.session_state.shape_collection:
        return False, "No shapes in collection to import."

    # Format the shape collection for import
    shapes_to_import = [
        {"path": item["path"], "name": item["name"]}
        for item in st.session_state.shape_collection
    ]

    # Perform the import
    successful, total = visio.import_multiple_shapes(
        shapes_to_import,
        doc_index,
        page_index
    )

    if successful == 0:
        return False, f"Failed to import any shapes. Verify Visio is running and document is open."
    elif successful < total:
        return True, f"Partially successful. Imported {successful} of {total} shapes."
    else:
        return True, f"Successfully imported all {total} shapes to Visio."

def toggle_favorite_stencil(stencil_path: str):
    """Add or remove a stencil from favorites using the database."""
    try:
        db = StencilDatabase()
        is_currently_fav = db.is_favorite_stencil(stencil_path)

        if is_currently_fav:
            # Remove from favorites
            db.remove_favorite_stencil(stencil_path)
            result = False # No longer a favorite
        else:
            # Add to favorites
            # We might need stencil details (name, shape_count) if we want to store them
            # directly in favorites table, but current DB schema doesn't store them there.
            # The add_favorite_stencil method only needs the path.
            result = db.add_favorite_stencil(stencil_path) # Returns True if added, False if error/already exists

        db.close()
        return result # True if added, False if removed or error
    except Exception as e:
        st.error(f"Error toggling favorite status: {str(e)}")
        import traceback
        st.text(traceback.format_exc())
        return False

def is_favorite_stencil(stencil_path: str) -> bool:
    """Check if a stencil is in favorites using the database."""
    try:
        db = StencilDatabase()
        is_fav = db.is_favorite_stencil(stencil_path)
        db.close()
        return is_fav
    except Exception as e:
        st.error(f"Error checking favorite status: {str(e)}")
        import traceback
        st.text(traceback.format_exc())
        return False

def toggle_show_favorites():
    """Toggle the favorites view"""
    st.session_state.show_favorites = not st.session_state.show_favorites

def toggle_options():
    """Toggle search options visibility"""
    st.session_state.show_filters = not st.session_state.show_filters

def search_stencils_db(search_term: str, filters: dict, directory_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search the stencil database using the optimized search method, supporting advanced search queries.

    Args:
        search_term (str): The user query string (AND/OR/phrases/NOT/property).
        filters (dict): Dictionary of filter values from session state.
        directory_filter (Optional[str]): Path to filter stencils by.

    Returns:
        List[Dict[str, Any]]: List of matching shapes with stencil info.
    """
    if not search_term:
        return []  # Don't search if term is empty

    try:
        # New: Advanced query parsing
        parsed_query = parse_search_query(search_term)

        # Build FTS string for DB
        fts_terms = []
        # AND logic: join with space
        if parsed_query["and"]:
            fts_terms.append(" ".join(f'"{t}"' if " " in t else t for t in parsed_query["and"]))
        # OR logic: join with OR syntax
        if parsed_query["or"]:
            or_group = " OR ".join(f'"{t}"' if " " in t else t for t in parsed_query["or"])
            fts_terms.append(f"({or_group})")
        # If nothing in AND/OR, fall back to empty string to avoid blank queries
        if not fts_terms:
            fts_str = ""
        else:
            fts_str = " ".join(fts_terms)

        db = StencilDatabase()
        use_fts = st.session_state.get('use_fts_search', True)
        # If no advanced query detected, fallback to raw search term
        db_search_term = fts_str if fts_str else search_term

        results = db.search_shapes(
            search_term=db_search_term,
            filters=filters,
            use_fts=use_fts,
            limit=st.session_state.get('search_result_limit', 1000),
            directory_filter=directory_filter
        )
        db.close()

        # Post-filter for NOT and properties
        filtered_results = []
        not_terms = set(t.lower() for t in parsed_query["not"])
        prop_filters = {k.lower(): v for k, v in parsed_query["properties"].items()}

        for row in results:
            # Gather all searchable fields into a lowercased string for NOT logic
            haystack = " ".join(
                str(row.get(k, "")).lower()
                for k in ("shape_name", "shape", "stencil_name", "description", "tags", "category")
                if k in row
            )
            # Exclude if any NOT term is present
            if any(nt in haystack for nt in not_terms):
                continue

            # Property filter: expects shape property dict/field in 'properties' or 'props'
            prop_data = row.get("properties") or row.get("props") or {}
            props_lc = {str(k).lower(): str(v).lower() for k, v in prop_data.items()} if isinstance(prop_data, dict) else {}
            prop_match = True
            for k, v in prop_filters.items():
                # supports substring match (case-insensitive) for property values
                valmatch = (
                    k in props_lc and v.lower() in str(props_lc[k]).lower()
                )
                if not valmatch:
                    prop_match = False
                    break
            if not prop_match and prop_filters:
                continue

            filtered_results.append(row)

        return filtered_results

    except Exception as e:
        st.error(f"Database search error: {e}")
        import traceback
        st.code(traceback.format_exc())
        return []

def search_current_document(search_term: str) -> List[Dict[str, Any]]:
    """
    Search for shapes in the current Visio document.

    Args:
        search_term (str): The term to search for in shape names or text.

    Returns:
        List[Dict[str, Any]]: A list of matching shapes with their properties.
    """
    if not search_term:
        return []  # Don't search if term is empty

    # Check if Visio is connected
    if not st.session_state.get('visio_connected', False):
        return []

    # Check if there are any open documents
    if not st.session_state.get('visio_documents', []):
        return []

    try:
        # Get the selected document index
        doc_index = st.session_state.selected_doc_index

        # Search for shapes in the document
        results = visio.search_shapes_in_document(doc_index, search_term)

        # Format the results to match the stencil search results format
        formatted_results = []
        for shape in results:
            formatted_result = {
                'shape_name': shape['name'] if shape['name'] else '(Unnamed Shape)',
                'shape_text': shape['text'],
                'stencil_name': f"Document: {st.session_state.visio_documents[doc_index-1]['name']} (Page: {shape['page_name']})",
                'stencil_path': f"visio_document_{doc_index}_{shape['page_index']}",  # Special path format to identify document shapes
                'shape_id': shape['id'],
                'page_index': shape['page_index'],
                'is_document_shape': True  # Flag to identify document shapes vs. stencil shapes
            }
            formatted_results.append(formatted_result)

        return formatted_results

    except Exception as e:
        st.error(f"Error searching current document: {e}")
        import traceback
        st.code(traceback.format_exc())
        return []

# Initialize session state variables if they don't exist
def initialize_session_state():
    if 'current_search_term' not in st.session_state:
        st.session_state.current_search_term = ""
    if 'last_search_input' not in st.session_state:
        st.session_state.last_search_input = ""
    # Ensure batch selection state is initialized if not done in app.py (belt-and-suspenders)
    if 'selected_shapes_for_batch' not in st.session_state:
        st.session_state.selected_shapes_for_batch = {}

# Callback to handle changes in batch selection checkboxes
def handle_batch_selection_change(shape_unique_id, shape_data):
    widget_key = f"select_batch_{shape_unique_id}"
    if st.session_state.get(widget_key):
        # Checkbox is checked, add/update shape data in selection dict
        st.session_state.selected_shapes_for_batch[shape_unique_id] = shape_data
    else:
        # Checkbox is unchecked, remove shape data from selection dict if it exists
        if shape_unique_id in st.session_state.selected_shapes_for_batch:
            del st.session_state.selected_shapes_for_batch[shape_unique_id]

# Callback to update the main search term state
def update_search_term():
    st.session_state.current_search_term = st.session_state.explorer_search_input_widget

def perform_search():
    """Execute search and update related state"""
    search_term = st.session_state.current_search_term
    active_directory = st.session_state.get('active_explorer_directory') # Get the active directory

    if search_term:
        # Add term to search history if it's not there already
        if search_term not in st.session_state.search_history:
            st.session_state.search_history.append(search_term)
            # Keep history to the most recent 10 items
            if len(st.session_state.search_history) > 10:
                st.session_state.search_history = st.session_state.search_history[-10:]

        # Get filters from session state
        filters = {
            'date_start': st.session_state.filter_date_start,
            'date_end': st.session_state.filter_date_end,
            'min_size': st.session_state.filter_min_size,
            'max_size': st.session_state.filter_max_size,
            'min_shapes': st.session_state.filter_min_shapes,
            'max_shapes': st.session_state.filter_max_shapes,
            'show_favorites': st.session_state.get('show_favorites_toggle', False),
            # Shape metadata filters
            'min_width': st.session_state.filter_min_width,
            'max_width': st.session_state.filter_max_width,
            'min_height': st.session_state.filter_min_height,
            'max_height': st.session_state.filter_max_height,
            'has_properties': st.session_state.filter_has_properties,
            'property_name': st.session_state.filter_property_name,
            'property_value': st.session_state.filter_property_value
        }

        # --- DEBUG PRINT ---
        print(f"--- Performing Search ---")
        print(f"Term: '{search_term}'")
        print(f"Filters: {filters}")
        print(f"Active Directory: {active_directory}")
        print(f"Search in Document: {st.session_state.get('search_in_document', False)}")
        # --- END DEBUG PRINT ---

        results = []

        # Search in stencil database, passing the active directory filter
        db_results = search_stencils_db(search_term, filters, directory_filter=active_directory)
        # Inject result_source for stencil_directory
        for r in db_results:
            r["result_source"] = "stencil_directory"
            # Also set shape_name fallback if not present
            if "shape_name" not in r and "shape" in r:
                r["shape_name"] = r["shape"]

        results.extend(db_results)

        # Search in current document if option is enabled
        if st.session_state.get('search_in_document', False):
            doc_results = search_current_document(search_term)
            # Inject result_source for visio_document
            for r in doc_results:
                r["result_source"] = "visio_document"
                if "shape_name" not in r and "shape" in r:
                    r["shape_name"] = r["shape"]
            # --- Add duplicate check ---
            existing_doc_shape_ids = {r['shape_id'] for r in results if r.get('is_document_shape')}
            for doc_shape in doc_results:
                if doc_shape['shape_id'] not in existing_doc_shape_ids:
                    results.append(doc_shape)
            # --- End duplicate check ---

        # --- Apply limit to the combined results ---
        limit = st.session_state.get('search_result_limit', 1000)
        final_results = results[:limit]
        # --- End limit application ---

        # Update search results
        st.session_state.search_results = final_results

    else: # Handle case where search term is empty
        st.session_state.search_results = []

def main(selected_directory=None):
    # Inject custom CSS styles for badges using unsafe_allow_html
    try:
        with open("custom_styles.css", "r") as f:
            custom_css = f.read()
        st.markdown(f"<style>{custom_css}</style>", unsafe_allow_html=True)
    except Exception:
        pass
    # No need to initialize session state here as it's done in app.py
    # Page title
    st.title("Visio Stencil Explorer")

    # Page description and About section
    st.markdown("Search for shapes and import them into Visio.")

    # About section using expander component like in the Temp File Cleaner page
    with st.expander("About Visio Stencil Explorer"):
        st.markdown("""
        ### Visio Stencil Explorer

        This application allows you to search for shapes within Visio stencil files,
        and within your current Visio document. You can:

        - Search for shapes by name across all stencils
        - Search for shapes within your current Visio document
        - Preview shapes from stencils
        - Select shapes in your current document directly from search results
        - Add shapes to a collection for quick access
        - Import shapes directly into Visio
        - Save favorite stencils for quick access

        Use the search options to filter and find exactly what you need.
        Enable "Search in Current Document" in the search options to find shapes in your open Visio document.

        ---
        ### Advanced Search Syntax

        You can use advanced queries in the search bar to find exactly what you need:

        **Supported features:**
        - **AND** (default): Separate terms by spaces. Both must match.
          `network switch` &rarr; finds shapes with both "network" and "switch"
        - **OR**: Use `OR` (uppercase) or `|`
          `router OR firewall` or `router | firewall`
        - **Phrases**: Use double quotes for exact phrases
          `"server rack"`
        - **NOT/Exclusion**: Use `-`, `!`, or `NOT`
          `cloud -azure` &rarr; finds "cloud" shapes that do **not** mention "azure"
          `server NOT dell`
          `!legacy`
        - **Property search**: Use `property:value` syntax to filter by shape property
          `manufacturer:Cisco`
          `category:"network device"`

        **Examples:**
        - `router OR switch -legacy`
          (router or switch, but not legacy models)
        - `"server rack" manufacturer:HPE`
        - `firewall category:security`
        - `cloud NOT azure NOT google`
        - `connector -3d`

        *All terms are case-insensitive. Property search matches substring within property values.*

        ---
        """)

    # --- Persistent User Preferences Sidebar Settings ---
    prefs = get_user_preferences()
    with st.sidebar:
        with st.expander("Settings", expanded=False):
            # UI Theme
            ui_theme = st.selectbox(
                "UI Theme",
                options=["default", "high_contrast"],
                index=["default", "high_contrast"].index(st.session_state.get("ui_theme", "default")),
                key="sidebar_ui_theme"
            )
            # Document search toggle
            document_search = st.checkbox(
                "Enable Document Search by Default",
                value=st.session_state.get("search_in_document", prefs.get("document_search")),
                key="sidebar_document_search"
            )
            # FTS toggle
            fts_toggle = st.checkbox(
                "Enable FTS (Full Text Search) by Default",
                value=st.session_state.get("use_fts_search", prefs.get("fts")),
                key="sidebar_fts"
            )
            # Results per page
            results_per_page = st.number_input(
                "Results Per Page",
                min_value=1,
                max_value=1000,
                value=st.session_state.get("search_result_limit", prefs.get("results_per_page")),
                key="sidebar_results_per_page"
            )
            # Pagination toggle
            pagination_enabled = st.checkbox(
                "Enable Pagination",
                value=st.session_state.get("pagination_enabled", prefs.get("pagination")),
                key="sidebar_pagination"
            )
            # Visio Auto Refresh
            visio_auto_refresh = st.checkbox(
                "Auto-Refresh Visio Connection",
                value=st.session_state.get("visio_auto_refresh", prefs.get("visio_auto_refresh")),
                key="sidebar_visio_auto_refresh"
            )

            updated = False
            # Handle updating preferences and synchronizing session state
            if ui_theme != st.session_state.get("ui_theme"):
                prefs.set("ui_theme", ui_theme)
                st.session_state.ui_theme = ui_theme
                updated = True
            if document_search != st.session_state.get("search_in_document"):
                prefs.set("document_search", document_search)
                st.session_state.search_in_document = document_search
                updated = True
            if fts_toggle != st.session_state.get("use_fts_search"):
                prefs.set("fts", fts_toggle)
                st.session_state.use_fts_search = fts_toggle
                updated = True
            if results_per_page != st.session_state.get("search_result_limit"):
                prefs.set("results_per_page", results_per_page)
                st.session_state.search_result_limit = results_per_page
                updated = True
            if pagination_enabled != st.session_state.get("pagination_enabled"):
                prefs.set("pagination", pagination_enabled)
                st.session_state.pagination_enabled = pagination_enabled
                updated = True
            if visio_auto_refresh != st.session_state.get("visio_auto_refresh"):
                prefs.set("visio_auto_refresh", visio_auto_refresh)
                st.session_state.visio_auto_refresh = visio_auto_refresh
                updated = True

            if updated:
                try:
                    prefs.save()
                except Exception as e:
                    st.error(f"Error saving preferences: {str(e)}")
                    import traceback
                    st.text(traceback.format_exc())
                st.success("Preferences updated and saved.", icon="✅")

            # Reset to defaults button: wipes prefs, resets session state, reruns app
            if st.button("Reset to defaults"):
                prefs.reset()
                for k, v in UserPreferences.defaults().items():
                    # Map preference keys to session state keys
                    keymap = {
                        "document_search": "search_in_document",
                        "fts": "use_fts_search",
                        "results_per_page": "search_result_limit",
                        "pagination": "pagination_enabled",
                        "ui_theme": "ui_theme",
                        "visio_auto_refresh": "visio_auto_refresh"
                    }
                    session_key = keymap[k]
                    st.session_state[session_key] = v
                st.success("Preferences reset to defaults. Reloading...", icon="🔄")
                st.experimental_rerun()

# --- Preview Cache Management Sidebar ---
        cache = PreviewCache()
        with st.expander("Preview Cache", expanded=False):
            stats = cache.cache_stats()
            st.markdown(f"**Cache Files:** {stats['files']}  \n**Total Size:** {stats['total_bytes'] / 1024:.1f} KB")
            if st.button("Clear Preview Cache"):
                removed = cache.clear_cache()
                st.success(f"Cleared {removed} cached previews.", icon="🗑️")
    # Determine the active directory
    directory_to_use = None
    directory_source = "unknown"

    if selected_directory: # Check if a directory path was passed from app.py
        if isinstance(selected_directory, str) and os.path.isdir(selected_directory):
            directory_to_use = selected_directory
            directory_source = "passed_from_app"
            # Check if it corresponds to an active preset for informational message
            try:
                db = StencilDatabase()
                active_preset = db.get_active_directory()
                db.close()
                if active_preset and active_preset['path'] == directory_to_use:
                    st.info(f"Using Active Preset Directory: {active_preset['name']} ({directory_to_use})")
            except Exception as e:
                st.error(f"Error checking active directory preset: {str(e)}")
                import traceback
                st.text(traceback.format_exc())
        else:
             # Invalid directory passed from app.py, try session state
             pass # Fall through to session state check
    
    if not directory_to_use:
        # Fallback to session state or config if nothing valid was passed
        last_dir_from_session = st.session_state.get('last_dir')
        if last_dir_from_session and os.path.isdir(last_dir_from_session):
            directory_to_use = last_dir_from_session
            directory_source = "session_state"
            st.info(f"Using Last Session Directory: {directory_to_use}")
        else:
            # Final fallback to config default
            config_default = config.get("paths.stencil_directory", "./test_data")
            if os.path.isdir(config_default):
                 directory_to_use = config_default
                 directory_source = "config_default"
                 st.warning(f"No valid directory selected. Using config default: {directory_to_use}")
            else:
                 directory_to_use = None # No valid directory found anywhere
                 directory_source = "none"
                 st.error("No valid stencil directory found or configured. Please select one in the sidebar.")

    # Store the determined directory for use in this page
    active_directory = directory_to_use
    # Update session state if the source wasn't session state itself
    if directory_source != "session_state" and active_directory:
        st.session_state.last_dir = active_directory 

    # Determine column ratio based on screen width
    browser_width = st.session_state.get('browser_width', 1200)  # Default to desktop
    if browser_width < 768:  # Mobile
        col_ratio = [1, 1]  # Equal columns on mobile (will stack vertically)
    elif browser_width < 992:  # Tablet
        col_ratio = [3, 2]  # Slightly more space for search
    else:  # Desktop
        col_ratio = [2, 1]  # Default ratio

    # Create two main columns for better layout
    search_col, workspace_col = st.columns(col_ratio)

    # Batch Actions are now handled in the main app sidebar

    # SEARCH COLUMN (Left) - Search and Results
    with search_col:
        # Search container - Simplified and focused on search function
        with st.container(border=True):
            st.write("### Search")

            # Search bar with buttons - Primary action at the top
            search_row = st.columns([5, 2, 1, 1])
            with search_row[0]:
                # Debounced search integration
                if "debouncer" not in st.session_state:
                    st.session_state.debouncer = DebounceSearch(perform_search, delay=0.5)
                debouncer = st.session_state.debouncer

                def debounced_update_search_term():
                    st.session_state.current_search_term = st.session_state.explorer_search_input_widget
                    debouncer.call()

                search_input = st.text_input(
                    "Search for shapes",
                    key="explorer_search_input_widget",
                    value=st.session_state.get('current_search_term', ''),
                    on_change=debounced_update_search_term,
                    label_visibility="collapsed"
                )
                # Handle Enter key press in the search input (immediate search)
                if search_input and search_input != st.session_state.get('last_search_input', ''):
                    st.session_state['last_search_input'] = search_input
                    debouncer.cancel()
                    perform_search()
            with search_row[1]:
                # This button triggers the search
                search_button = st.button("Search", use_container_width=True)
            with search_row[2]:
                # Options button at half width
                options_btn = st.button("Options", key="options_btn", use_container_width=True)
            with search_row[3]:
                # New refresh button
                refresh_btn = st.button("Refresh", key="refresh_btn", use_container_width=True)

            if search_button:
                perform_search()
            if options_btn:
                toggle_options()
            if refresh_btn:
                # Refresh the search results if there's an active search
                if st.session_state.get('current_search_term', ''):
                    perform_search()
                # Also refresh Visio connection
                with st.spinner("Refreshing Visio connection..."):
                    refresh_visio_connection()

            # Search options caption
            st.caption("Need to filter results? Use the Options button.")

            # Search options - When expanded
            if st.session_state.show_filters:
                # Add CSS to ensure sliders in the expander span full width
                st.markdown("""
                <style>
                /* Ensure sliders in the search options expander span full width */
                div[data-testid="stExpander"] div[data-testid="stSlider"] {
                    width: 100% !important;
                }
                div[data-testid="stExpander"] div[data-testid="stSlider"] > div {
                    width: 100% !important;
                }
                </style>
                """, unsafe_allow_html=True)

                with st.expander("Search Options", expanded=True):
                    # Search options in two columns
                    options_col1, options_col2 = st.columns(2)

                    with options_col1:
                        # Favorites checkbox
                        st.checkbox("Show Favorites Only",
                            value=st.session_state.show_favorites,
                            key="show_favorites_toggle",
                            help="Only show shapes from favorite stencils")

                        # Search in document option - only enabled if Visio is connected
                        visio_connected = st.session_state.get('visio_connected', False)
                        visio_has_docs = len(st.session_state.get('visio_documents', [])) > 0
                        search_doc_disabled = not (visio_connected and visio_has_docs)

                        search_doc_tooltip = "Search for shapes in the current Visio document"
                        if search_doc_disabled:
                            if not visio_connected:
                                search_doc_tooltip = "Connect to Visio first to enable this option"
                            elif not visio_has_docs:
                                search_doc_tooltip = "Open a document in Visio first to enable this option"

                        # Toggle: include shapes from active Visio document
                        st.session_state.search_in_document = st.checkbox(
                            "Include Visio Document Shapes",
                            value=st.session_state.search_in_document,
                            key="search_in_document", # i18n key: search_in_document
                            help="If enabled, searches both the stencil directory and the currently open Visio document for shapes. " + search_doc_tooltip,
                            disabled=search_doc_disabled
                        )

                        # Update session state and trigger search if changed
                        if st.session_state.search_in_document != st.session_state.get('search_in_document_last_state', False):
                            st.session_state.search_in_document_last_state = st.session_state.search_in_document
                            # Trigger a new search if there's an active search term
                            if st.session_state.get('current_search_term', ''):
                                perform_search()

                    with options_col2:
                        # Search method options
                        st.checkbox("Use Fast Search (FTS)",
                                key="use_fts_search",
                                help="Toggle between fast full-text search and standard search. Fast search is more efficient but might miss some partial matches.")

                        st.number_input("Result Limit",
                                min_value=100,
                                max_value=10000,
                                step=100,
                                key="search_result_limit",
                                help="Maximum number of search results to display")

                    # Date filters
                    st.write("##### Date Filters")
                    # Add spacing before date inputs for better readability
                    inject_spacer(10)
                    date_col1, date_col2 = st.columns(2)
                    with date_col1:
                        st.date_input("From Date",
                                key="filter_date_start",
                                value=None,
                                help="Filter stencils by modification date (starting from)")
                    with date_col2:
                        st.date_input("To Date",
                                key="filter_date_end",
                                value=None,
                                help="Filter stencils by modification date (ending at)")
                    # Add spacing after date inputs
                    inject_spacer(10)

                    # Size and shape count filters
                    st.write("##### Size and Shape Filters")

                    # Add CSS to fix slider appearance and make them different widths
                    st.markdown("""
                    <style>
                    /* Hide the default slider values that appear on the right side */
                    div[data-testid="stSlider"] > div > div:last-child {
                        display: none;
                    }

                    /* File Size slider - make it shorter */
                    [data-testid="stSlider"][aria-labelledby*="file_size_range"] {
                        width: 75% !important;
                    }

                    /* Shape Count slider - make it longer */
                    [data-testid="stSlider"][aria-labelledby*="shape_count_range"] {
                        width: 100% !important;
                    }

                    /* Add custom labels for min/max values */
                    [data-testid="stSlider"][aria-labelledby*="file_size_range"]::before {
                        content: "0";
                        position: absolute;
                        bottom: 0;
                        left: 0;
                        font-size: 14px;
                        color: rgba(255, 255, 255, 0.7);
                    }
                    [data-testid="stSlider"][aria-labelledby*="file_size_range"]::after {
                        content: "50";
                        position: absolute;
                        bottom: 0;
                        right: 0;
                        font-size: 14px;
                        color: rgba(255, 255, 255, 0.7);
                    }
                    [data-testid="stSlider"][aria-labelledby*="shape_count_range"]::before {
                        content: "0";
                        position: absolute;
                        bottom: 0;
                        left: 0;
                        font-size: 14px;
                        color: rgba(255, 255, 255, 0.7);
                    }
                    [data-testid="stSlider"][aria-labelledby*="shape_count_range"]::after {
                        content: "500";
                        position: absolute;
                        bottom: 0;
                        right: 0;
                        font-size: 14px;
                        color: rgba(255, 255, 255, 0.7);
                    }
                    </style>
                    """, unsafe_allow_html=True)

                    # File Size slider
                    st.slider("File Size (MB)",
                            min_value=0,
                            max_value=50, # 50 MB
                            value=(0, 50),
                            step=1,
                            format="%d", # Format as integer without leading zeros
                            key="file_size_range",
                            label_visibility="visible",
                            help="Filter stencils by file size in megabytes")

                    # Update individual min/max size for the filter dict
                    # Convert MB to bytes
                    if 'file_size_range' in st.session_state:
                        st.session_state.filter_min_size = st.session_state.file_size_range[0] * 1024 * 1024
                        st.session_state.filter_max_size = st.session_state.file_size_range[1] * 1024 * 1024

                    # Add spacing between sliders
                    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

                    # Shape Count slider
                    st.slider("Shape Count",
                            min_value=0,
                            max_value=500,
                            value=(0, 500),
                            step=1,
                            format="%d", # Format as integer without leading zeros
                            key="shape_count_range",
                            label_visibility="visible",
                            help="Filter stencils by number of shapes")

                    # Add spacing after sliders
                    inject_spacer(10)

                    # Update individual min/max shape count for the filter dict
                    if 'shape_count_range' in st.session_state:
                        st.session_state.filter_min_shapes = st.session_state.shape_count_range[0]
                        st.session_state.filter_max_shapes = st.session_state.shape_count_range[1]

                    # Shape metadata filters
                    st.write("##### Shape Metadata Filters")
                    inject_spacer(10)

                    # Width and height filters
                    metadata_col1, metadata_col2 = st.columns(2)
                    with metadata_col1:
                        st.number_input("Min Width",
                                min_value=0.0,
                                max_value=100.0,
                                step=0.1,
                                key="filter_min_width",
                                help="Filter shapes by minimum width")
                    with metadata_col2:
                        st.number_input("Max Width",
                                min_value=0.0,
                                max_value=100.0,
                                step=0.1,
                                key="filter_max_width",
                                help="Filter shapes by maximum width (0 = no limit)")

                    with metadata_col1:
                        st.number_input("Min Height",
                                min_value=0.0,
                                max_value=100.0,
                                step=0.1,
                                key="filter_min_height",
                                help="Filter shapes by minimum height")
                    with metadata_col2:
                        st.number_input("Max Height",
                                min_value=0.0,
                                max_value=100.0,
                                step=0.1,
                                key="filter_max_height",
                                help="Filter shapes by maximum height (0 = no limit)")

                    # Property filters
                    st.checkbox("Has Properties",
                            key="filter_has_properties",
                            help="Only show shapes that have custom properties")

                    prop_col1, prop_col2 = st.columns(2)
                    with prop_col1:
                        st.text_input("Property Name",
                                key="filter_property_name",
                                help="Filter by specific property name")
                    with prop_col2:
                        st.text_input("Property Value",
                                key="filter_property_value",
                                help="Filter by specific property value")

                    # Display options
                    st.write("##### Display Options")
                    st.checkbox("Show Metadata Columns",
                            key="show_metadata_columns",
                            help="Show shape metadata columns in search results")

                    # Reset filters button
                    if st.button("Reset Filters", key="reset_filters"):
                        st.session_state.filter_date_start = None
                        st.session_state.filter_date_end = None
                        st.session_state.filter_min_size = 0
                        st.session_state.filter_max_size = 50 * 1024 * 1024
                        st.session_state.filter_min_shapes = 0
                        st.session_state.filter_max_shapes = 500
                        st.session_state.filter_min_width = 0
                        st.session_state.filter_max_width = 0
                        st.session_state.filter_min_height = 0
                        st.session_state.filter_max_height = 0
                        st.session_state.filter_has_properties = False
                        st.session_state.filter_property_name = ""
                        st.session_state.filter_property_value = ""
                        st.session_state.show_favorites = False
                        st.session_state.show_metadata_columns = False
                        st.rerun()

            # Recent searches - More prominent placement
            if st.session_state.search_history:
                st.write("##### Recent Searches")

                # Add custom CSS for consistent spacing in search history buttons
                st.markdown("""
                <style>
                    /* Add consistent spacing to search history buttons */
                    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
                        padding: 0 5px;
                    }
                    /* Add margin to the buttons */
                    div[data-testid="stHorizontalBlock"] button {
                        margin: 5px 0;
                    }
                </style>
                """, unsafe_allow_html=True)

                # Add spacing before search history
                inject_spacer(10)

                # Use a container to ensure consistent spacing
                with st.container():
                    history_cols = st.columns(min(5, len(st.session_state.search_history)))
                    for i, term in enumerate(reversed(st.session_state.search_history)):
                        col_idx = i % 5
                        with history_cols[col_idx]:
                            if st.button(term, key=f"history_{i}", use_container_width=True):
                                # Use this search term - update current_search_term
                                st.session_state.current_search_term = term

                                filters = {
                                    'date_start': st.session_state.filter_date_start,
                                    'date_end': st.session_state.filter_date_end,
                                    'min_size': st.session_state.filter_min_size,
                                    'max_size': st.session_state.filter_max_size,
                                    'min_shapes': st.session_state.filter_min_shapes,
                                    'max_shapes': st.session_state.filter_max_shapes,
                                    # Include metadata filters
                                    'min_width': st.session_state.filter_min_width,
                                    'max_width': st.session_state.filter_max_width,
                                    'min_height': st.session_state.filter_min_height,
                                    'max_height': st.session_state.filter_max_height,
                                    'has_properties': st.session_state.filter_has_properties,
                                    'property_name': st.session_state.filter_property_name,
                                    'property_value': st.session_state.filter_property_value
                                }
                                # Perform search immediately after setting term
                                st.session_state.search_results = search_stencils_db(st.session_state.current_search_term, filters, directory_filter=active_directory)
                                # Rerun to update the input field display and results
                                st.rerun()

                # Add spacing after search history
                inject_spacer(10)

            # Tools section - Moved to bottom of search container
            st.write("##### Tools")
            update_btn = st.button("Update Cache", key="update_btn", use_container_width=True,
                                  help="Scan the active directory and update the stencil cache")

            # Add spacing between Update Cache button and scanning status
            inject_spacer(15)

            # Handle scanning - Remains outside the form
            if update_btn and not st.session_state.background_scan_running:
                scan_dir = st.session_state.get('active_explorer_directory') # Use the active directory
                if not scan_dir or not os.path.exists(scan_dir):
                    st.error(f"Active directory does not exist or is not set: {scan_dir}")
                else:
                    background_scan(scan_dir) # Pass the active directory to the scan function

            # Show scan progress if running - Remains outside the form
            if st.session_state.background_scan_running:
                st.progress(st.session_state.scan_progress / 100)
                st.caption(st.session_state.scan_status)
                # Add spacer after scanning progress
                inject_spacer(20)

        # Display search results - Remains outside the form
        # Phase 1 addition: st.info banner if search_in_document is OFF, show only once per session
        if not st.session_state.get("search_in_document", False):
            if not st.session_state.get("info_banner_shown", False):
                st.info("Document search is currently OFF. Only shapes from the stencil directory will appear below. Enable 'Include Visio Document Shapes' in Options to search the open Visio document.")
                st.session_state.info_banner_shown = True

        if st.session_state.search_results:
            with st.container(border=True):
                st.write(f"### Results ({len(st.session_state.search_results)} shapes found)")

                # Create a DataFrame for the results with optional metadata columns
                if st.session_state.show_metadata_columns:
                    # Determine which columns to show based on screen width
                    browser_width = st.session_state.get('browser_width', 1200)
                    if browser_width < 768:  # Mobile
                        # On mobile, show minimal columns
                        df = pd.DataFrame([
                            {
                                "Shape": item.get("shape", "N/A"),
                                "Stencil": item.get("stencil_name", "N/A"),
                                "Width": item.get("width", 0),
                                "Height": item.get("height", 0)
                            } for item in st.session_state.search_results if isinstance(item, dict)
                        ])
                    else:  # Tablet and Desktop
                        df = pd.DataFrame([
                            {
                                "Shape": item.get("shape", "N/A"),
                                "Stencil": item.get("stencil_name", "N/A"),
                                "Path": item.get("stencil_path", "N/A"),
                                "Width": item.get("width", 0),
                                "Height": item.get("height", 0),
                                "Properties": len(item.get("properties", {}))
                            } for item in st.session_state.search_results if isinstance(item, dict)
                        ])
                else:
                    # Determine which columns to show based on screen width
                    browser_width = st.session_state.get('browser_width', 1200)
                    if browser_width < 768:  # Mobile
                        # On mobile, show minimal columns
                        df = pd.DataFrame([
                            {
                                "Shape": item.get("shape", "N/A"),
                                "Stencil": item.get("stencil_name", "N/A")
                            } for item in st.session_state.search_results if isinstance(item, dict)
                        ])
                    else:  # Tablet and Desktop
                        df = pd.DataFrame([
                            {
                                "Shape": item.get("shape", "N/A"),
                                "Stencil": item.get("stencil_name", "N/A"),
                                "Path": item.get("stencil_path", "N/A")
                            } for item in st.session_state.search_results if isinstance(item, dict)
                        ])

                # Show the results with improved styling
                # ---- Phase 1: Grouping and badges with st.tabs ----
                # Group by result_source
                results = st.session_state.search_results
                stencil_results = [r for r in results if r.get("result_source") == "stencil_directory"]
                doc_results = [r for r in results if r.get("result_source") == "visio_document"]
                has_both_sources = len(stencil_results) > 0 and len(doc_results) > 0

                def render_results_group(results_group):
                    for idx, result in enumerate(results_group):
                        with st.container():
                            is_document_shape = result.get("result_source") == "visio_document"
                            badge_html = ""
                            if is_document_shape:
                                badge_html = '<span class="badge-source badge-document">Document</span>'
                            else:
                                badge_html = '<span class="badge-source badge-stencil">Stencil</span>'

                            # Standard fields
                            shape = result.get("shape_name") or result.get("shape", "N/A")
                            stencil = result.get("stencil_name", "N/A")
                            path = result.get("stencil_path", "N/A")

                            # Example display: [badge] Shape name (Stencil)
                            st.markdown(
                                f"{badge_html} **{shape}**  <span style='color: #888'>({stencil})</span>",
                                unsafe_allow_html=True,
                            )
                            # Optionally show more shape info or actions here
                            # ...

                if has_both_sources:
                    tab_labels = ["All", "Stencil", "Document"]
                    tabs = st.tabs(tab_labels)
                    # All
                    with tabs[0]:
                        render_results_group(results)
                    # Stencil only
                    with tabs[1]:
                        render_results_group(stencil_results)
                    # Document only
                    with tabs[2]:
                        render_results_group(doc_results)
                else:
                    render_results_group(results)
                # ---- End Phase 1 grouping and badges ----


        elif st.session_state.current_search_term and not st.session_state.search_results:
            st.info("No shapes found matching your search criteria.")

    # WORKSPACE COLUMN (Right) - Collection, Integration, Preview
    with workspace_col:
        # Shape collection panel - Positioned at top as primary workspace
        with st.container(border=True):
            st.write("### Shape Collection")

            if st.session_state.shape_collection:
                for idx, item in enumerate(st.session_state.shape_collection):
                    st.markdown(f"**{item['name']}**")
                    st.caption(item['stencil_name'])
                    # Use a single column for the remove button to avoid unused variable warnings
                    _, button_col = st.columns([5, 1])
                    with button_col:
                        st.button("🗑️", key=f"remove_{idx}", help="Remove from collection",
                                on_click=remove_from_collection, args=(idx,))
                    st.divider()

                # Clear button
                _, btn_col = st.columns([3, 1])
                with btn_col:
                    if st.button("Clear All", key="clear_collection"):
                        clear_collection()
            else:
                st.info("No shapes in collection. Add shapes from search results.")

        # Visio integration - Logically follows collection for workflow
        with st.container(border=True):
            # Title and refresh button in one row
            title_col, refresh_col = st.columns([4, 1])

            with title_col:
                st.write("### Visio Integration")

            with refresh_col:
                refresh_visio = st.button("🔄", key="refresh_visio", help="Refresh Visio Connection")

            # Handle Visio connection
            if refresh_visio:
                with st.spinner("Connecting to Visio..."):
                    refresh_visio_connection()

            # Show connection status
            if st.session_state.visio_connected:
                if st.session_state.visio_documents:
                    st.success(f"Connected to Visio ({len(st.session_state.visio_documents)} document(s) open)")

                    # Always show document selector when documents are available
                    doc_options = {f"{doc['name']}": doc['index'] for doc in st.session_state.visio_documents}

                    # Find the index of the currently selected document in the options list
                    current_doc_index = 0
                    for i, (_, idx) in enumerate(doc_options.items()):
                        if idx == st.session_state.selected_doc_index:
                            current_doc_index = i
                            break

                    selected_doc_name = st.selectbox(
                        "Select Visio Document",
                        options=list(doc_options.keys()),
                        index=current_doc_index,
                        key="doc_selector"
                    )
                    selected_doc_index = doc_options[selected_doc_name]

                    # Update session state if changed
                    if selected_doc_index != st.session_state.selected_doc_index:
                        st.session_state.selected_doc_index = selected_doc_index
                        # When document changes, reset page selection
                        st.session_state.selected_page_index = 1
                        st.rerun()

                    # Get pages for the selected document
                    pages = visio.get_pages_in_document(selected_doc_index)

                    if pages:
                        # Show page selector
                        # Create labeled page options directly without an intermediate variable
                        labeled_page_options = {}
                        for page in pages:
                            label = f"{page['name']}"
                            if page['is_schematic']:
                                label += " (Schematic)"
                            labeled_page_options[label] = page['index']

                        # Find index of current selection in options list
                        current_page_index = st.session_state.selected_page_index
                        default_index = 0
                        for i, (_, idx) in enumerate(labeled_page_options.items()):
                            if idx == current_page_index:
                                default_index = i
                                break

                        selected_page_label = st.selectbox(
                            "Select Page",
                            options=list(labeled_page_options.keys()),
                            index=default_index,
                            key="page_selector"
                        )
                        selected_page_index = labeled_page_options[selected_page_label]

                        # Update session state if changed
                        if selected_page_index != st.session_state.selected_page_index:
                            st.session_state.selected_page_index = selected_page_index
                    else:
                        st.warning("No pages found in the selected document")
                        selected_page_index = 1

                    # Import button with better alignment
                    if st.session_state.shape_collection:
                        if st.button("Import to Visio", key="import_to_visio", use_container_width=True):
                            with st.spinner("Importing shapes to Visio..."):
                                success, message = import_collection_to_visio(
                                    st.session_state.selected_doc_index,
                                    st.session_state.selected_page_index
                                )
                                if success:
                                    st.success(message)
                                else:
                                    st.error(message)
                else:
                    st.warning("Connected to Visio, but no documents open.")
                    # Offer to create a new document
                    create_doc_col1, create_doc_col2 = st.columns([3, 2])
                    with create_doc_col1:
                        new_doc_name = st.text_input("New document name", value="New Document", key="new_doc_name")
                    with create_doc_col2:
                        if st.button("Create New Document"):
                            with st.spinner("Creating new Visio document..."):
                                success = visio.create_new_document(new_doc_name)
                                if success:
                                    st.success(f"Created new document: {new_doc_name}")
                                    # Refresh the document list
                                    refresh_visio_connection()
                                    st.rerun()
                                else:
                                    st.error("Failed to create new document")
            else:
                st.error("Not connected to Visio")
                # Check if Visio is installed but not running
                if visio.is_visio_installed():
                    st.info("Visio is installed but not running. Please start Visio and click the refresh button.")
                    if st.button("Launch Visio", key="launch_visio_btn"):
                        with st.spinner("Launching Visio..."):
                            success = visio.launch_visio()
                            if success:
                                st.success("Visio launched successfully")
                                # Wait a moment for Visio to initialize
                                time.sleep(2)
                                # Try to connect
                                refresh_visio_connection()
                                st.rerun()
                            else:
                                st.error("Failed to launch Visio")
                else:
                    st.info("Visio does not appear to be installed or accessible. Please install Visio or check your configuration.")

        # Show shape preview if selected - Placed at the bottom of workspace
        if st.session_state.preview_shape:
            with st.container(border=True):
                st.write("### Shape Preview")
                shape_data = st.session_state.preview_shape
                st.caption(f"From: {shape_data['stencil_name']}")

                # Add spacing for better preview layout
                inject_spacer(10)

                # Add custom CSS for better image padding and centering
                st.markdown("""
                <style>
                    /* Improve image padding and centering in preview */
                    div[data-testid="stImage"] {
                        padding: 15px;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                    }
                    div[data-testid="stImage"] > img {
                        max-width: 90%;
                        max-height: 90%;
                        object-fit: contain;
                    }
                </style>
                """, unsafe_allow_html=True)

                # Get shape preview with metadata if available
                # --- Use PreviewCache for shape preview performance ---
                cache = st.session_state.get("preview_cache_instance")
                if cache is None:
                    cache = PreviewCache()
                    st.session_state.preview_cache_instance = cache

                preview_key = f"{shape_data['stencil_path']}::{shape_data['name']}"

                preview = cache.get_cached_preview(preview_key)
                if preview is None:
                    preview = get_shape_preview(
                        shape_data['stencil_path'],
                        shape_data['name'],
                        shape_data=shape_data if 'geometry' in shape_data else None
                    )
                    if preview:
                        cache.save_preview(preview_key, preview)
                if preview:
                    st.image(preview, use_container_width=True, caption=shape_data['name'])

                    # Show metadata if available
                    if 'width' in shape_data and shape_data['width'] > 0:
                        st.caption(f"Width: {shape_data['width']:.2f}, Height: {shape_data['height']:.2f}")

                    # Show properties if available and not empty
                    if 'properties' in shape_data and shape_data['properties']:
                        st.write("##### Properties")

                        # Determine layout based on screen width and number of properties
                        browser_width = st.session_state.get('browser_width', 1200)
                        num_properties = len(shape_data['properties'])

                        if browser_width < 768 or num_properties > 5:  # Mobile or many properties
                            # Use a vertical layout with expandable sections for many properties
                            with st.expander("View All Properties", expanded=(num_properties <= 5)):
                                for key, value in shape_data['properties'].items():
                                    st.markdown(f"**{key}**: {value}")
                        else:  # Desktop with few properties
                            # Use a dataframe for a more compact display
                            props_df = pd.DataFrame([
                                {"Property": key, "Value": value}
                                for key, value in shape_data['properties'].items()
                            ])
                            st.dataframe(props_df, use_container_width=True)
                else:
                    st.error("Unable to generate preview")

                inject_spacer(10)

                if st.button("Close Preview", key="close_preview"):
                    st.session_state.preview_shape = None
                    st.rerun()

# Only call main() when run directly
if __name__ == "__main__":
    main()
# When imported, main() is called from app.py
