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

from app.core import config
from app.core import scan_directory, parse_visio_stencil, get_shape_preview, visio, directory_preset_manager
from app.core.db import StencilDatabase
from app.core.components import render_shared_sidebar
from app.core.custom_styles import inject_spacer

# Page config is now set in app.py to avoid the 'set_page_config must be first' error
# st.set_page_config(
#     page_title=config.get("app.title", "Visio Stencil Explorer"),
#     page_icon="🔍",
#     layout="wide",
#     initial_sidebar_state="expanded",
# )

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

def is_favorite_stencil(stencil_path: str) -> bool:
    """Check if a stencil is in favorites using the database."""
    db = StencilDatabase()
    is_fav = db.is_favorite_stencil(stencil_path)
    db.close()
    return is_fav

def toggle_show_favorites():
    """Toggle the favorites view"""
    st.session_state.show_favorites = not st.session_state.show_favorites

def toggle_options():
    """Toggle search options visibility"""
    st.session_state.show_filters = not st.session_state.show_filters

def search_stencils_db(search_term: str, filters: dict, directory_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Search the stencil database using the optimized search method.

    Args:
        search_term (str): The term to search for in shape names.
        filters (dict): A dictionary containing filter values from session state.
        directory_filter (Optional[str]): Path to filter stencils by.

    Returns:
        List[Dict[str, Any]]: A list of matching shapes with stencil info.
    """
    if not search_term:
        return []  # Don't search if term is empty

    try:
        db = StencilDatabase()
        # Use the new optimized search method
        use_fts = st.session_state.get('use_fts_search', True)
        results = db.search_shapes(
            search_term=search_term,
            filters=filters,
            use_fts=use_fts,
            limit=st.session_state.get('search_result_limit', 1000),
            directory_filter=directory_filter # Pass directory_filter to db method
        )
        db.close()
        return results

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
        print(f"Search in Document: {st.session_state.get('search_in_document_checkbox', False)}")
        # --- END DEBUG PRINT ---

        # Initialize results list
        results = []

        # Search in stencil database, passing the active directory filter
        db_results = search_stencils_db(search_term, filters, directory_filter=active_directory)
        results.extend(db_results)

        # Search in current document if option is enabled
        if st.session_state.get('search_in_document_checkbox', False):
            doc_results = search_current_document(search_term)
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
        """)

    # Determine the active directory
    directory_to_use = None
    directory_source = "unknown"

    if selected_directory: # Check if a directory path was passed from app.py
        if isinstance(selected_directory, str) and os.path.isdir(selected_directory):
            directory_to_use = selected_directory
            directory_source = "passed_from_app"
            # Check if it corresponds to an active preset for informational message
            db = StencilDatabase()
            active_preset = db.get_active_directory()
            db.close()
            if active_preset and active_preset['path'] == directory_to_use:
                st.info(f"Using Active Preset Directory: {active_preset['name']} ({directory_to_use})")
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
                # Use the new key and on_change callback, value from current_search_term
                search_input = st.text_input("Search for shapes",
                              key="explorer_search_input_widget",
                              value=st.session_state.get('current_search_term', ''),
                              on_change=update_search_term,
                              label_visibility="collapsed")
                # Handle Enter key press in the search input
                if search_input and search_input != st.session_state.get('last_search_input', ''):
                    st.session_state['last_search_input'] = search_input
                    # Only trigger search if the input has changed
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

                        search_in_doc = st.checkbox("Search in Current Document",
                            value=st.session_state.search_in_document,
                            key="search_in_document",
                            help=search_doc_tooltip,
                            disabled=search_doc_disabled)

                        # Update session state and trigger search if changed
                        if search_in_doc != st.session_state.get('search_in_document_last_state', False):
                            st.session_state.search_in_document_last_state = search_in_doc
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
                for idx, row in df.iterrows():
                    with st.container():
                        # Check if this is a document shape (from current document search)
                        is_document_shape = False
                        original_result = st.session_state.search_results[idx]
                        if 'is_document_shape' in original_result and original_result['is_document_shape']:
                            is_document_shape = True
                            shape_id = original_result.get('shape_id')
                            page_index = original_result.get('page_index')

                        # Use consistent column layout for all shapes
                        # Adjust column widths based on screen size
                        browser_width = st.session_state.get('browser_width', 1200)
                        if browser_width < 768:  # Mobile
                            # Checkbox, Shape/Stencil, Action1
                            res_col_cb, res_col1, res_col2 = st.columns([1, 4, 1])
                            res_col3 = res_col2  # Use same column for both actions
                        else:  # Tablet and Desktop
                            # Checkbox, Shape/Stencil, Action1, Action2
                            res_col_cb, res_col1, res_col2, res_col3 = st.columns([1, 5, 1, 1])

                        # --- Checkbox Column ---
                        with res_col_cb:
                            # Need a unique ID for each shape row for the selection state
                            # Combine path and name for stencils, use shape_id for doc shapes
                            if is_document_shape:
                                shape_unique_id = f"doc_{shape_id}"
                            else:
                                shape_unique_id = f"stencil_{row['Path']}_{row['Shape']}"

                            # Get the full data for this shape to store on selection
                            full_shape_data = original_result

                            # Render the checkbox
                            st.checkbox("", # No visible label
                                        key=f"select_batch_{shape_unique_id}",
                                        value=(shape_unique_id in st.session_state.selected_shapes_for_batch),
                                        on_change=handle_batch_selection_change,
                                        args=(shape_unique_id, full_shape_data),
                                        label_visibility="collapsed"
                                        )

                        with res_col1:
                            # Use the original_result we already have
                            shape_name = row['Shape']

                            # Check if we have highlight information
                            if 'highlight_start' in original_result and original_result['highlight_start'] >= 0:
                                # Create highlighted text
                                start = original_result['highlight_start']
                                end = original_result['highlight_end']
                                highlighted_name = (
                                    f"{shape_name[:start]}"
                                    f"<span style='background-color: #ffff00;'>{shape_name[start:end]}</span>"
                                    f"{shape_name[end:]}"
                                )
                                st.markdown(f"**{highlighted_name}**", unsafe_allow_html=True)
                            else:
                                # No highlight information, just show the name
                                st.markdown(f"**{shape_name}**")

                            st.caption(f"{row['Stencil']}")

                            # For document shapes, show a different icon/indicator
                            if is_document_shape:
                                st.caption("📄 Shape in current document")
                            else:
                                st.caption(f"{row['Path']}")

                        with res_col2:
                            if is_document_shape:
                                # For document shapes, show a select button instead of preview
                                if st.button("🔍", key=f"select_{idx}", help="Select this shape in Visio"):
                                    # Get the document index
                                    doc_index = st.session_state.selected_doc_index

                                    # Select the shape in Visio
                                    success = visio.select_shape(doc_index, page_index, shape_id)
                                    if success:
                                        st.success(f"Selected shape in Visio")
                                    else:
                                        st.error("Failed to select shape")
                            else:
                                # For stencil shapes, show the preview button
                                if st.button("👁️", key=f"preview_{idx}", help="Preview shape"):
                                    # Get the original result with all metadata
                                    original_result = st.session_state.search_results[idx]

                                    # Set the shape for preview with metadata if available
                                    preview_data = {
                                        "name": row['Shape'],
                                        "stencil_name": row['Stencil'],
                                        "stencil_path": row['Path'],
                                        "width": original_result.get("width", 0),
                                        "height": original_result.get("height", 0),
                                        "geometry": original_result.get("geometry", []),
                                        "properties": original_result.get("properties", {})
                                    }
                                    toggle_shape_preview(preview_data)

                        with res_col3:
                            # Add to collection button (for both types)
                            if st.button("➕", key=f"add_{idx}", help="Add to collection"):
                                add_to_collection(row['Shape'], row['Stencil'], row['Path'])

                # Export options
                st.divider()
                st.caption("Export Results")
                export_col1, export_col2, export_col3 = st.columns(3)

                with export_col1:
                    st.markdown(generate_export_link(df, 'csv'), unsafe_allow_html=True)
                with export_col2:
                    st.markdown(generate_export_link(df, 'excel'), unsafe_allow_html=True)
                with export_col3:
                    st.markdown(generate_export_link(df, 'txt'), unsafe_allow_html=True)
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
                preview = get_shape_preview(
                    shape_data['stencil_path'],
                    shape_data['name'],
                    shape_data=shape_data if 'geometry' in shape_data else None
                )
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
