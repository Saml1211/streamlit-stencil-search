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

# Page config is now set in app.py to avoid the 'set_page_config must be first' error
# st.set_page_config(
#     page_title=config.get("app.title", "Visio Stencil Explorer"),
#     page_icon="🔍",
#     layout="wide",
#     initial_sidebar_state="expanded",
# )

# Initialize session state
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
# Search history initialization
if 'search_history' not in st.session_state:
    st.session_state.search_history = []
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
# Shape collection initialization
if 'shape_collection' not in st.session_state:
    st.session_state.shape_collection = []
# Search in document option
if 'search_in_document' not in st.session_state:
    st.session_state.search_in_document = False
# Visio connection status
if 'visio_connected' not in st.session_state:
    st.session_state.visio_connected = False
if 'visio_documents' not in st.session_state:
    st.session_state.visio_documents = []
if 'selected_doc_index' not in st.session_state:
    st.session_state.selected_doc_index = 1
if 'selected_page_index' not in st.session_state:
    st.session_state.selected_page_index = 1
# Favorites initialization
if 'favorite_stencils' not in st.session_state:
    st.session_state.favorite_stencils = []
if 'show_favorites' not in st.session_state:
    st.session_state.show_favorites = False
# Search options
if 'show_filters' not in st.session_state:
    st.session_state.show_filters = False
if 'use_fts_search' not in st.session_state:
    st.session_state.use_fts_search = True
if 'search_result_limit' not in st.session_state:
    st.session_state.search_result_limit = 1000
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

# Use the shared sidebar component
selected_directory = render_shared_sidebar(key_prefix="p1_")

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

def search_stencils_db(search_term: str, filters: dict) -> List[Dict[str, Any]]:
    """
    Search the stencil database using the optimized search method.

    Args:
        search_term (str): The term to search for in shape names.
        filters (dict): A dictionary containing filter values from session state.

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
            limit=st.session_state.get('search_result_limit', 1000)
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

# Callback to update the main search term state
def update_search_term():
    st.session_state.current_search_term = st.session_state.search_input_widget

def perform_search():
    """Execute search and update related state"""
    search_term = st.session_state.current_search_term
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
            'show_favorites': st.session_state.get('show_favorites_toggle', False)
        }

        # Initialize results list
        results = []

        # Search in stencil database
        db_results = search_stencils_db(search_term, filters)
        results.extend(db_results)

        # Search in current document if option is enabled
        if st.session_state.get('search_in_document', False):
            doc_results = search_current_document(search_term)
            results.extend(doc_results)

        # Update search results
        st.session_state.search_results = results

def main():
    initialize_session_state()
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

    # Create two main columns for better layout
    search_col, workspace_col = st.columns([2, 1])

    # Use the root_dir from the session state with a fallback default
    if 'last_dir' in st.session_state:
        root_dir = st.session_state.last_dir
    else:
        # Fallback to a default directory
        root_dir = config.get("paths.stencil_directory", "./test_data")
        # Store it in session state for next time
        st.session_state.last_dir = root_dir

    # SEARCH COLUMN (Left) - Search and Results
    with search_col:
        # Search container - Simplified and focused on search function
        with st.container(border=True):
            st.write("### Search")

            # Search bar with button - Primary action at the top
            search_row = st.columns([5, 1])
            with search_row[0]:
                # Use the new key and on_change callback, value from current_search_term
                search_input = st.text_input("Search for shapes",
                              key="search_input_widget",
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

            if search_button:
                perform_search()

            # Search options toggle - Remains outside the form
            options_row = st.columns([5, 1])
            with options_row[0]:
                st.caption("Need to filter results? Use search options.")
            with options_row[1]:
                options_btn = st.button("Options", key="options_btn")
                if options_btn:
                    toggle_options()

            # Search options - When expanded
            if st.session_state.show_filters:
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

                        st.checkbox("Search in Current Document",
                            value=st.session_state.search_in_document,
                            key="search_in_document_toggle",
                            help=search_doc_tooltip,
                            disabled=search_doc_disabled)

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

                    # Size and shape count filters
                    st.write("##### Size and Shape Filters")
                    # File size filters
                    st.slider("File Size (KB)",
                            min_value=0,
                            max_value=int(50 * 1024), # 50 MB in KB
                            value=(0, int(50 * 1024)),
                            key="file_size_range",
                            help="Filter stencils by file size")

                    # Update individual min/max size for the filter dict
                    # Convert KB to bytes
                    if 'file_size_range' in st.session_state:
                        st.session_state.filter_min_size = st.session_state.file_size_range[0] * 1024
                        st.session_state.filter_max_size = st.session_state.file_size_range[1] * 1024

                    # Shape count filters
                    st.slider("Shape Count",
                            min_value=0,
                            max_value=500,
                            value=(0, 500),
                            key="shape_count_range",
                            help="Filter stencils by number of shapes")

                    # Update individual min/max shape count for the filter dict
                    if 'shape_count_range' in st.session_state:
                        st.session_state.filter_min_shapes = st.session_state.shape_count_range[0]
                        st.session_state.filter_max_shapes = st.session_state.shape_count_range[1]

                    # Reset filters button
                    if st.button("Reset Filters", key="reset_filters"):
                        st.session_state.filter_date_start = None
                        st.session_state.filter_date_end = None
                        st.session_state.filter_min_size = 0
                        st.session_state.filter_max_size = 50 * 1024 * 1024
                        st.session_state.filter_min_shapes = 0
                        st.session_state.filter_max_shapes = 500
                        st.session_state.show_favorites = False
                        st.rerun()

            # Recent searches - More prominent placement
            if st.session_state.search_history:
                st.write("##### Recent Searches")
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
                                'max_shapes': st.session_state.filter_max_shapes
                            }
                            # Perform search immediately after setting term
                            st.session_state.search_results = search_stencils_db(st.session_state.current_search_term, filters)
                            # Rerun to update the input field display and results
                            st.rerun()

            # Tools section - Moved to bottom of search container
            st.write("##### Tools")
            update_btn = st.button("Update Cache", key="update_btn", use_container_width=True,
                                  help="Scan directories and update the stencil cache")

            # Handle scanning - Remains outside the form
            if update_btn and not st.session_state.background_scan_running:
                if not os.path.exists(root_dir):
                    st.error(f"Directory does not exist: {root_dir}")
                else:
                    background_scan(root_dir)

            # Show scan progress if running - Remains outside the form
            if st.session_state.background_scan_running:
                st.progress(st.session_state.scan_progress / 100)
                st.caption(st.session_state.scan_status)

        # Display search results - Remains outside the form
        if st.session_state.search_results:
            with st.container(border=True):
                st.write(f"### Results ({len(st.session_state.search_results)} shapes found)")

                # Create a DataFrame for the results
                df = pd.DataFrame([
                    {
                        "Shape": item["shape"],
                        "Stencil": item["stencil_name"],
                        "Path": item["stencil_path"]
                    } for item in st.session_state.search_results
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

                        # Use different column layout based on shape type
                        if is_document_shape:
                            res_col1, res_col2, res_col3 = st.columns([5, 1, 1])
                        else:
                            res_col1, res_col2, res_col3 = st.columns([5, 1, 1])

                        with res_col1:
                            st.markdown(f"**{row['Shape']}**")
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
                                    # Set the shape for preview
                                    toggle_shape_preview({
                                        "name": row['Shape'],
                                        "stencil_name": row['Stencil'],
                                        "stencil_path": row['Path']
                                    })

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
                    col1, col2 = st.columns([5, 1])
                    with col2:
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

                    # If multiple documents are open, show a document selector
                    if len(st.session_state.visio_documents) > 1:
                        doc_options = {f"{doc['name']}": doc['index'] for doc in st.session_state.visio_documents}
                        selected_doc_name = st.selectbox(
                            "Select Visio Document",
                            options=list(doc_options.keys()),
                            index=0,
                            key="doc_selector"
                        )
                        selected_doc_index = doc_options[selected_doc_name]

                        # Update session state if changed
                        if selected_doc_index != st.session_state.selected_doc_index:
                            st.session_state.selected_doc_index = selected_doc_index
                            # When document changes, reset page selection
                            st.session_state.selected_page_index = 1
                            st.rerun()
                    else:
                        # Single document, use it automatically
                        selected_doc_index = st.session_state.selected_doc_index

                    # Get pages for the selected document
                    pages = visio.get_pages_in_document(selected_doc_index)

                    if pages:
                        # Show page selector
                        page_options = {f"{page['name']}": page['index'] for page in pages}

                        # Add "is_schematic" indicator to page names
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
                    st.warning("Connected to Visio, but no documents open. Please open a document in Visio and refresh.")
            else:
                st.error("Not connected to Visio")
                st.info("Make sure Visio is running and click the refresh button.")

        # Show shape preview if selected - Placed at the bottom of workspace
        if st.session_state.preview_shape:
            with st.container(border=True):
                st.write("### Shape Preview")
                shape_data = st.session_state.preview_shape
                st.caption(f"From: {shape_data['stencil_name']}")

                # Get shape preview
                preview = get_shape_preview(shape_data['stencil_path'], shape_data['name'])
                if preview:
                    st.image(preview, use_column_width=True, caption=shape_data['name'])
                else:
                    st.error("Unable to generate preview")

                if st.button("Close Preview", key="close_preview"):
                    st.session_state.preview_shape = None
                    st.rerun()

# Call main() only once
if __name__ == "__main__":
    main()
else:
    main()
