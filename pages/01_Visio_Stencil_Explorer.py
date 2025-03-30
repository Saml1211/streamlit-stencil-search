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

from app.core import scan_directory, parse_visio_stencil, config, get_shape_preview, visio
from app.core.db import StencilDatabase

# Set page config
st.set_page_config(
    page_title=config.get("app.title", "Visio Stencil Explorer"),
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for improved UI
st.markdown("""
<style>
    /* Improved container spacing */
    div.block-container {padding-top: 1rem;}
    
    /* Better button styling */
    .stButton button {
        width: 100%;
        border-radius: 4px;
    }
    
    /* Improved metrics styling */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem;
        font-weight: bold;
    }
    
    /* Container styling */
    [data-testid="stHorizontalBlock"] {
        gap: 0.5rem;
    }
    
    /* Better sidebar spacing */
    section[data-testid="stSidebar"] .block-container {
        padding-top: 2rem;
    }
    
    /* Search box styling */
    [data-testid="stTextInput"] input {
        border-radius: 4px;
    }
    
    /* Better header spacing */
    h1, h2, h3, h4 {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Card-like containers */
    [data-testid="stVerticalBlock"] > div[style] > div[data-testid="stVerticalBlock"] {
        background-color: #f8f9fa;
        padding: 0.75rem;
        border-radius: 4px;
        border: 1px solid #dee2e6;
        margin-bottom: 1rem;
    }
    
    /* Responsive adjustments */
    @media (max-width: 768px) {
        [data-testid="stMetricValue"] {
            font-size: 1.2rem;
        }
    }
</style>
""", unsafe_allow_html=True)

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

def get_layout_columns():
    """Get column layout based on screen width"""
    # Get current browser width using JavaScript
    width = st.session_state.get('browser_width', 1200)  # Default to desktop
    
    if width < 768:  # Mobile
        return [1, 1, 1]  # Stack columns vertically
    elif width < 992:  # Tablet
        return [2, 1, 2]  # Slightly compressed
    else:  # Desktop
        return [3, 2, 3]  # Full width

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

def use_search_history(term):
    """Use a previous search term from history"""
    # This function will be called when a previous search is clicked
    return term

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
    """Refresh the connection to Visio and update document list"""
    # Attempt to connect to Visio
    connected = visio.connect()
    st.session_state.visio_connected = connected
    
    # Get list of open documents
    if connected:
        st.session_state.visio_documents = visio.get_open_documents()
        # Reset selected document/page if none available
        if not st.session_state.visio_documents:
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

# --- New Database Search Function ---
def search_stencils_db(search_term: str, filters: dict) -> List[Dict[str, Any]]:
    """
    Search the stencil database using SQL based on term and filters.

    Args:
        search_term (str): The term to search for in shape names.
        filters (dict): A dictionary containing filter values from session state.

    Returns:
        List[Dict[str, Any]]: A list of matching shapes with stencil info.
    """
    results = []
    if not search_term:
        return results # Don't search if term is empty

    try:
        db = StencilDatabase() # Assumes db.py is accessible
        conn = db._get_conn() # Use internal method to get connection

        # Base query joining stencils and shapes
        sql = """
            SELECT s.name as shape_name, st.name as stencil_name, st.path as stencil_path
            FROM shapes s
            JOIN stencils st ON s.stencil_path = st.path
            WHERE s.name LIKE ?
        """
        params = [f"%{search_term}%"]

        # Add filters dynamically
        if filters.get('date_start'):
            sql += " AND st.last_modified >= ?"
            # Convert date to ISO format string if needed, assuming DB stores as TEXT ISO
            params.append(filters['date_start'].isoformat())
        if filters.get('date_end'):
            sql += " AND st.last_modified <= ?"
            # Add time component for inclusive end date? Or handle in query?
            # For simplicity, using <= date string. Might need adjustment based on DB storage.
            end_date_inclusive = filters['date_end'] + timedelta(days=1)
            params.append(end_date_inclusive.isoformat()) # Compare up to the start of the next day
        if filters.get('min_size') is not None:
             # Check if slider is not at default min
            if filters['min_size'] > 0:
                sql += " AND st.file_size >= ?"
                params.append(filters['min_size'])
        if filters.get('max_size') is not None:
             # Check if slider is not at default max (adjust 50*1024*1024 if needed)
            if filters['max_size'] < (50 * 1024 * 1024): # Example max check
                sql += " AND st.file_size <= ?"
                params.append(filters['max_size'])
        if filters.get('min_shapes') is not None:
            # Check if slider is not at default min
            if filters['min_shapes'] > 0:
                sql += " AND st.shape_count >= ?"
                params.append(filters['min_shapes'])
        if filters.get('max_shapes') is not None:
            # Check if slider is not at default max (adjust 500 if needed)
            if filters['max_shapes'] < 500: # Example max check
                sql += " AND st.shape_count <= ?"
                params.append(filters['max_shapes'])

        sql += " ORDER BY st.name, s.name" # Add ordering

        cursor = conn.execute(sql, tuple(params))

        # Format results
        for row in cursor.fetchall():
            results.append({
                'shape': row['shape_name'],
                'stencil_name': row['stencil_name'],
                'stencil_path': row['stencil_path'],
                # Add highlight info if needed (can be done post-query)
                'highlight_start': row['shape_name'].lower().find(search_term.lower()),
                'highlight_end': row['shape_name'].lower().find(search_term.lower()) + len(search_term)
            })

    except Exception as e:
        st.error(f"Database search error: {e}")
    finally:
        if 'db' in locals() and db:
            db.close() # Ensure connection is closed

    return results
# --- End Database Search Function ---

def main():
    # Inject JavaScript to track window width
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
    
    # Check for mobile display
    is_mobile = st.session_state.get('browser_width', 1200) < 768
    
    # Page title and description
    st.title("Visio Stencil Explorer")
    
    # About section with persistent state
    if 'show_about' not in st.session_state:
        st.session_state.show_about = False
        
    about_col1, about_col2 = st.columns([6, 1])
    with about_col1:
        if is_mobile:
            st.write("Search and manage your Visio stencils.")
        else:
            st.write("""
            Search through your Visio stencils, preview shapes, and manage your collection. 
            Use advanced filters to find exactly what you need.
            """)
    with about_col2:
        if st.button("ℹ️ About", key="about_button", use_container_width=True):
            st.session_state.show_about = not st.session_state.show_about
    
    if st.session_state.show_about:
        app_version = config.get("app.version", "1.0.0")
        with st.container(border=True):
            st.markdown(f"""
            ### Visio Stencil Explorer & Tools v{app_version}
            
            This application provides tools for working with Microsoft Visio files:
            
            1. **Stencil Explorer** (this page): Search for shapes across multiple Visio stencil files.
            2. **Temp File Cleaner**: Find and remove corrupted Visio temporary files that can cause issues.
            3. **Stencil Health**: Analyze stencils for issues such as duplicates or empty files.
            
            #### Key Features
            
            - Fast shape searching across stencils
            - Detailed file location information
            - Shape preview functionality
            - Shape collection for batch operations
            - Export search results to CSV/Excel
            - Search history for quick access
            - Direct Visio shape import
            - Favorites system for bookmarking
            - Mobile-responsive design
            """)
            
            # Close button
            if st.button("Close", key="close_about"):
                st.session_state.show_about = False
                st.rerun()
    
    # Create a main content and collection sidebar layout
    main_col, collection_col = st.columns([4, 1])
    
    with main_col:
        # Configuration in sidebar
        st.sidebar.markdown("<h3>Settings</h3>", unsafe_allow_html=True)
        
        # Get default directory from config
        default_dir = config.get("paths.stencil_directory", "./test_data")
        if not os.path.exists(default_dir):
            default_dir = "./test_data" if os.path.exists("./test_data") else "Z:/ENGINEERING TEMPLATES/VISIO SHAPES 2025"
        
        # Directory input with responsive layout
        if is_mobile:
            dir_col1, dir_col2 = st.sidebar.columns([4, 1])
            with dir_col1:
                root_dir = st.text_input("Directory:", 
                                      value=default_dir, key="dir_input")
            with dir_col2:
                st.write("")  # Spacing
                st.write("")  # Spacing
                update_btn = st.button("🔄", help="Update Now", key="update_btn_small")
        else:
            root_dir = st.sidebar.text_input("Stencil Directory", 
                                          value=default_dir, key="dir_input_large")
            update_col1, update_col2 = st.sidebar.columns([1, 1])
            with update_col1:
                update_btn = st.button("🔄 Update Now", use_container_width=True, key="update_btn_large")
            with update_col2:
                # Auto-refresh toggle and interval from config
                auto_refresh_interval = config.get("scanner.auto_refresh_interval", 1)
                auto_refresh = st.checkbox("Auto Refresh", value=(auto_refresh_interval > 0),
                                          help=f"Refresh every {auto_refresh_interval} hour(s)", key="auto_refresh")
        
        # Advanced Search Filters in sidebar
        st.sidebar.markdown("<h3>Advanced Filters</h3>", unsafe_allow_html=True)
        
        # Initialize filter session state
        if 'show_filters' not in st.session_state:
            st.session_state.show_filters = False
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
        
        # Toggle for advanced filters
        show_filters = st.sidebar.checkbox("Show Advanced Filters", value=st.session_state.show_filters, key="show_filters_toggle")
        st.session_state.show_filters = show_filters
        
        # Only show filters if toggle is on
        if st.session_state.show_filters:
            with st.sidebar.container(border=True):
                # Date filters
                st.sidebar.markdown("**Date Modified**")
                date_col1, date_col2 = st.sidebar.columns(2)
                with date_col1:
                    st.session_state.filter_date_start = st.date_input(
                        "From", value=st.session_state.filter_date_start,
                        key="date_start"
                    )
                with date_col2:
                    st.session_state.filter_date_end = st.date_input(
                        "To", value=st.session_state.filter_date_end,
                        key="date_end"
                    )
                
                # File size filters
                st.sidebar.markdown("**File Size (MB)**")
                # Convert bytes to MB (÷ 1024*1024)
                size_values = [st.session_state.filter_min_size/(1024*1024), st.session_state.filter_max_size/(1024*1024)]
                min_size, max_size = st.sidebar.slider(
                    "Size Range", 
                    min_value=0.0, 
                    max_value=50.0,  # Now in MB directly
                    value=size_values,
                    step=0.5,  # Smaller step in MB (0.5 MB increments)
                    key="size_slider"
                )
                # Convert back from MB to bytes for storage
                st.session_state.filter_min_size = min_size * (1024 * 1024)  # Convert back to bytes
                st.session_state.filter_max_size = max_size * (1024 * 1024)  # Convert back to bytes
                
                # Shape count filters
                st.sidebar.markdown("**Shape Count**")
                shape_values = [st.session_state.filter_min_shapes, st.session_state.filter_max_shapes]
                min_shapes, max_shapes = st.sidebar.slider(
                    "Shape Range", 
                    min_value=0, 
                    max_value=500, 
                    value=shape_values,
                    step=5,
                    key="shape_slider"
                )
                st.session_state.filter_min_shapes = min_shapes
                st.session_state.filter_max_shapes = max_shapes
                
                # Reset filters button
                if st.sidebar.button("Reset Filters", key="reset_filters"):
                    st.session_state.filter_date_start = None
                    st.session_state.filter_date_end = None
                    st.session_state.filter_min_size = 0
                    st.session_state.filter_max_size = 50 * 1024 * 1024
                    st.session_state.filter_min_shapes = 0
                    st.session_state.filter_max_shapes = 500
                    st.rerun()

        # Favorites toggle in sidebar
        st.sidebar.markdown("<h3>Favorites</h3>", unsafe_allow_html=True)
        show_favorites = st.sidebar.checkbox(
            "Show Favorites Only", 
            value=st.session_state.show_favorites,
            key="show_favorites_toggle"
        )
        if show_favorites != st.session_state.show_favorites:
            st.session_state.show_favorites = show_favorites
            st.rerun()
        
        # Handle scanning
        if update_btn and not st.session_state.background_scan_running:
            if not os.path.exists(root_dir):
                st.error(f"Directory does not exist: {root_dir}")
            else:
                background_scan(root_dir)
        
        # Show scan progress if running
        if st.session_state.background_scan_running:
            st.progress(st.session_state.scan_progress / 100)
            st.caption(st.session_state.scan_status)
        
        # Main search interface
        st.markdown("### Search Stencils")
        
        # Search history
        if st.session_state.search_history:
            st.caption("Recent Searches:")
            history_cols = st.columns(min(5, len(st.session_state.search_history)))
            for i, term in enumerate(st.session_state.search_history[-5:]):
                with history_cols[i % 5]:
                    # Use a stateless key based callback approach for history items
                    if st.button(term, key=f"history_{i}"):
                        # Store the term in a different session state variable
                        st.session_state.selected_history_term = term
                        st.rerun()  # Trigger a rerun to apply the term
        
        # Handle setting the search term from history before the widget is created
        if 'selected_history_term' in st.session_state:
            search_term = st.session_state.selected_history_term
            # Clear it after use
            del st.session_state.selected_history_term
        else:
            search_term = st.session_state.get('search_term', '')
            
        # Main search input
        search_term = st.text_input("Search for shapes", 
                                  value=search_term,
                                  key="search_term", 
                                  help="Enter shape name to search")
        
        # Search actions
        search_col1, search_col2 = st.columns([1, 4])
        with search_col1:
            if st.button("🔍 Search", key="search_button", use_container_width=True):
                if search_term:
                    # Get filter values from session state
                    filters = {
                        'date_start': st.session_state.filter_date_start,
                        'date_end': st.session_state.filter_date_end,
                        'min_size': st.session_state.filter_min_size,
                        'max_size': st.session_state.filter_max_size,
                        'min_shapes': st.session_state.filter_min_shapes,
                        'max_shapes': st.session_state.filter_max_shapes,
                        'show_favorites': st.session_state.show_favorites
                    }
                    
                    # Perform search using database with filters
                    results = search_stencils_db(search_term, filters)
                    st.session_state.search_results = results
                    
                    # Only add to history if it's a new term
                    if search_term not in st.session_state.search_history:
                        st.session_state.search_history.append(search_term)
        with search_col2:
            if st.button("🗑️ Clear", key="clear_button"):
                # Use a flag to clear the search term instead of directly modifying it
                st.session_state.clear_search = True
                st.session_state.search_results = []
                st.rerun()
        
        # Handle clear flag (before the widget is created)
        if st.session_state.get('clear_search', False):
            search_term = ""  # Set empty value
            st.session_state.clear_search = False  # Reset the flag
        
        # Display search results
        if st.session_state.search_results:
            st.success(f"Found {len(st.session_state.search_results)} results")
            
            # Create columns for the results table
            col_sizes = get_layout_columns()
            col1, col2, col3 = st.columns(col_sizes)
            col1.markdown("**Shape**")
            col2.markdown("**Stencil**")
            col3.markdown("**Actions**")
            
            # Display results
            for result in st.session_state.search_results:
                col1, col2, col3 = st.columns(col_sizes)
                col1.write(result['shape'])
                col2.write(result['stencil_name'])
                with col3:
                    st.button("👁️ Preview", key=f"preview_{result['shape']}", 
                             on_click=toggle_shape_preview, args=(result,))
                    st.button("➕ Add", key=f"add_{result['shape']}", 
                             on_click=add_to_collection, 
                             args=(result['shape'], result['stencil_name'], result['stencil_path']))
    
    with collection_col:
        # Shape collection panel
        st.markdown("### Shape Collection")
        if st.session_state.shape_collection:
            for idx, item in enumerate(st.session_state.shape_collection):
                with st.container(border=True):
                    st.write(f"**{item['name']}**")
                    st.caption(item['stencil_name'])
                    st.button("🗑️", key=f"remove_{idx}", 
                             on_click=remove_from_collection, args=(idx,))
            
            if st.button("Clear All", key="clear_collection"):
                clear_collection()
        else:
            st.info("No shapes in collection")
            
        # Visio integration
        st.markdown("### Visio Integration")
        if st.button("🔄 Refresh Connection", key="refresh_visio"):
            refresh_visio_connection()
        
        if st.session_state.visio_connected:
            st.success("Connected to Visio")
            if st.session_state.shape_collection:
                if st.button("📥 Import to Visio", key="import_to_visio"):
                    success, message = import_collection_to_visio(
                        st.session_state.selected_doc_index,
                        st.session_state.selected_page_index
                    )
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
        else:
            st.warning("Not connected to Visio")

# Call main() only once using if/else pattern
if __name__ == "__main__":
    main()
else:
    main()
