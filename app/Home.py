import streamlit as st
import os
import sys
import time
import pandas as pd
import io
import base64
from datetime import datetime, timedelta
import threading
from typing import List, Dict, Any, Optional # Added typing import

# Add the parent directory to path so we can import from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import scan_directory, parse_visio_stencil, config, get_shape_preview, visio
from app.core.db import StencilDatabase # Added StencilDatabase import

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
    # Create a main content and collection sidebar layout with better proportions
    main_col, collection_col = st.columns([4, 1])
    
    with main_col:
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
        
        # App header with better styling
        st.markdown(f"<h1 style='margin-bottom: 1.5rem;'>{config.get('app.title', 'Visio Stencil Explorer')}</h1>", unsafe_allow_html=True)
        
        # About section with persistent state
        if 'show_about' not in st.session_state:
            st.session_state.show_about = False
            
        if st.button("ℹ️ About Stencil Explorer", use_container_width=False):
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
        
        # Configuration
        st.sidebar.markdown("<h3>Settings</h3>", unsafe_allow_html=True)
        
        # Get default directory from config
        default_dir = config.get("paths.stencil_directory", "./test_data")
        if not os.path.exists(default_dir):
            default_dir = "./test_data" if os.path.exists("./test_data") else "Z:/ENGINEERING TEMPLATES/VISIO SHAPES 2025"
        
        # Improved responsive directory input
        if st.session_state.get('browser_width', 1200) < 768:
            dir_col1, dir_col2 = st.sidebar.columns([4, 1])
            with dir_col1:
                root_dir = st.text_input("Directory:", 
                                      value=default_dir)
            with dir_col2:
                st.write("")  # Spacing
                st.write("")  # Spacing
                update_btn = st.button("🔄", help="Update Now")
        else:
            root_dir = st.sidebar.text_input("Stencil Directory", 
                                          value=default_dir)
            update_col1, update_col2 = st.sidebar.columns([1, 1])
            with update_col1:
                update_btn = st.button("🔄 Update Now", use_container_width=True)
            with update_col2:
                # Auto-refresh toggle and interval from config
                auto_refresh_interval = config.get("scanner.auto_refresh_interval", 1)
                auto_refresh = st.checkbox("Auto Refresh", value=(auto_refresh_interval > 0),
                                          help=f"Refresh every {auto_refresh_interval} hour(s)")
        
        # --- Advanced Filters with Collapsible UI ---
        st.sidebar.markdown("---")
        with st.sidebar.expander("Advanced Filters", expanded=False):
            # Date Range Filter (Last Modified)
            today = datetime.now().date()
            one_year_ago = today - timedelta(days=365)
            date_range = st.date_input(
                "Last Modified Date",
                value=(one_year_ago, today),
                max_value=today,
                help="Filter stencils based on their last modified date."
            )
            st.session_state.filter_date_start = date_range[0] if len(date_range) > 0 else None
            st.session_state.filter_date_end = date_range[1] if len(date_range) > 1 else None

            # File Size Filter - with improved and consistent labeling
            st.markdown("<p style='margin-bottom: 0.5rem;'>File Size (MB)</p>", unsafe_allow_html=True)
            size_col1, size_col2 = st.columns(2)
            with size_col1:
                min_size_mb = st.number_input("Min", 
                                             min_value=0.0, 
                                             max_value=50.0, 
                                             value=0.0, 
                                             step=0.1,
                                             label_visibility="visible")
            with size_col2:
                max_size_mb = st.number_input("Max", 
                                             min_value=0.0, 
                                             max_value=50.0, 
                                             value=50.0, 
                                             step=0.1,
                                             label_visibility="visible")
            
            st.session_state.filter_min_size = int(min_size_mb * 1024 * 1024)  # Convert to bytes
            st.session_state.filter_max_size = int(max_size_mb * 1024 * 1024)  # Convert to bytes

            # Shape Count Filter - with improved and consistent labeling
            st.markdown("<p style='margin-bottom: 0.5rem;'>Shape Count</p>", unsafe_allow_html=True)
            shape_col1, shape_col2 = st.columns(2)
            with shape_col1:
                min_shapes = st.number_input("Min", 
                                            min_value=0, 
                                            max_value=500, 
                                            value=0,
                                            key="min_shapes",
                                            label_visibility="visible")
            with shape_col2:
                max_shapes = st.number_input("Max", 
                                            min_value=0, 
                                            max_value=500, 
                                            value=500,
                                            key="max_shapes",
                                            label_visibility="visible")
            
            st.session_state.filter_min_shapes = min_shapes
            st.session_state.filter_max_shapes = max_shapes

        # --- Improved Saved Searches UI ---
        st.sidebar.markdown("---")
        with st.sidebar.expander("Saved Searches", expanded=False):
            db = StencilDatabase()
            saved_searches = db.get_saved_searches()
            db.close()

            saved_search_options = {f"{s['name']}": s for s in saved_searches}
            options_list = ["-- Select Saved Search --"] + list(saved_search_options.keys())

            selected_saved_search_label = st.selectbox(
                "Load Search",
                options=options_list,
                index=0,
                key="saved_search_selector",
                help="Select a saved search to load its term and filters."
            )

            # Logic to load the selected search
            if selected_saved_search_label != options_list[0]:
                selected_search_data = saved_search_options[selected_saved_search_label]
                loaded_filters = selected_search_data['filters']

                # Update session state filters - with careful date conversion
                try:
                    st.session_state.filter_date_start = datetime.fromisoformat(loaded_filters['date_start']).date() if loaded_filters.get('date_start') else None
                    st.session_state.filter_date_end = datetime.fromisoformat(loaded_filters['date_end']).date() if loaded_filters.get('date_end') else None
                except (ValueError, TypeError): # Handle potential errors during conversion
                     st.session_state.filter_date_start = None
                     st.session_state.filter_date_end = None
                     st.warning("Could not load date filters from saved search.")

                st.session_state.filter_min_size = loaded_filters.get('min_size')
                st.session_state.filter_max_size = loaded_filters.get('max_size')
                st.session_state.filter_min_shapes = loaded_filters.get('min_shapes')
                st.session_state.filter_max_shapes = loaded_filters.get('max_shapes')

                # Update the main search term input widget's value
                # This requires modifying the search_term text_input later
                st.session_state.loaded_search_term = selected_search_data['search_term']

                # Reset the selectbox to placeholder after loading to prevent re-loading on every interaction
                st.session_state.saved_search_selector = options_list[0]

                # Rerun to apply the loaded term and filters to the UI widgets
                st.rerun()

            # Improved delete UI with confirmation
            if selected_saved_search_label != options_list[0]:
                delete_col1, delete_col2 = st.columns([3, 1])
                with delete_col2:
                    delete_btn = st.button("🗑️ Delete", key="delete_saved_search")
                
                if delete_btn:
                    confirm_delete = st.checkbox(f"Confirm deletion of '{selected_saved_search_label}'?")
                    if confirm_delete:
                        search_to_delete = saved_search_options[selected_saved_search_label]
                        db = StencilDatabase()
                        db.delete_saved_search(search_to_delete['id'])
                        db.close()
                        st.success(f"Deleted saved search '{selected_saved_search_label}'.")
                        st.session_state.saved_search_selector = options_list[0]
                        st.rerun()

        # --- Improved Tools UI ---
        st.sidebar.markdown("---")
        st.sidebar.markdown("<h3>Tools</h3>", unsafe_allow_html=True)
        
        # Highlight new feature with better styling
        st.sidebar.markdown("""
        <div style="background-color: #e6f3ff; padding: 10px; border-radius: 5px; border-left: 4px solid #0066cc;">
            <p style="margin: 0; color: #0066cc;">✨ <strong>NEW</strong>: Bookmark your favorite stencils for quick access!</p>
        </div>
        """, unsafe_allow_html=True)

        # Background scan status with improved progress display
        if st.session_state.background_scan_running:
            st.sidebar.markdown("<p style='margin-top:10px;'>Scanning in progress...</p>", unsafe_allow_html=True)
            st.sidebar.progress(st.session_state.scan_progress, 
                             text=st.session_state.scan_status)
        elif st.session_state.last_background_scan:
            st.sidebar.caption(f"Last scan: {st.session_state.last_background_scan.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Auto-refresh check
        if (auto_refresh and 
            st.session_state.last_background_scan and 
            datetime.now() - st.session_state.last_background_scan > timedelta(hours=auto_refresh_interval) and
            not st.session_state.background_scan_running):
            update_btn = True
        
        # Favorites toggle button with improved styling
        if st.session_state.favorite_stencils:
            fav_btn_label = "⭐ Show Favorites" if not st.session_state.show_favorites else "🔍 Show All Stencils"
            st.sidebar.button(fav_btn_label, on_click=toggle_show_favorites, use_container_width=True)
            
            # Display favorites with improved card UI
            if st.session_state.show_favorites:
                st.markdown("<h2>⭐ Favorite Items</h2>", unsafe_allow_html=True)
                db = StencilDatabase()
                favorites = db.get_favorites()
                db.close()

                if not favorites:
                    st.info("You haven't added any favorites yet. Click the ☆ icon next to a stencil in search results.")

                # Use grid layout for favorites on larger screens
                if st.session_state.get('browser_width', 1200) >= 992:
                    fav_cols = st.columns(2)
                    for i, fav in enumerate(favorites):
                        col_idx = i % 2
                        with fav_cols[col_idx]:
                            with st.container(border=True):
                                st.markdown(f"**{fav['stencil_name']}**")
                                st.caption(f"Path: {fav['stencil_path']}")
                                btn_col1, btn_col2 = st.columns(2)
                                if btn_col1.button("👁️ View", key=f"view_fav_{fav['id']}", use_container_width=True):
                                    db_view = StencilDatabase()
                                    stencil_to_view = db_view.get_stencil_by_path(fav['stencil_path'])
                                    db_view.close()
                                    if stencil_to_view:
                                        st.session_state.selected_stencil = stencil_to_view
                                        st.rerun()
                                    else:
                                        st.error("Could not load stencil details.")
                                if btn_col2.button("⭐ Remove", key=f"unfav_{fav['id']}", 
                                                 help="Remove from favorites", use_container_width=True):
                                    db_remove = StencilDatabase()
                                    db_remove.remove_favorite(fav['id'])
                                    db_remove.close()
                                    st.rerun()
                else:
                    # Single column layout for smaller screens
                    for i, fav in enumerate(favorites):
                        with st.container(border=True):
                            st.markdown(f"**{fav['stencil_name']}**")
                            st.caption(f"Path: {fav['stencil_path']}")
                            btn_col1, btn_col2 = st.columns(2)
                            if btn_col1.button("👁️ View", key=f"view_fav_{fav['id']}", use_container_width=True):
                                db_view = StencilDatabase()
                                stencil_to_view = db_view.get_stencil_by_path(fav['stencil_path'])
                                db_view.close()
                                if stencil_to_view:
                                    st.session_state.selected_stencil = stencil_to_view
                                    st.rerun()
                            if btn_col2.button("⭐ Remove", key=f"unfav_{fav['id']}", 
                                             help="Remove from favorites", use_container_width=True):
                                db_remove = StencilDatabase()
                                db_remove.remove_favorite(fav['id'])
                                db_remove.close()
                                st.rerun()
                
                st.markdown("---")
        
        # Improved search UI with better layout
        st.markdown("<h2>Search</h2>", unsafe_allow_html=True)
        # Adjust column proportions to give more space to the buttons
        search_col1, search_col2, search_col3 = st.columns([3, 0.7, 0.7])
        
        with search_col1:
            # Use the loaded search term if available
            initial_search_term = st.session_state.pop('loaded_search_term', '')
            search_term = st.text_input(
                "Search shapes:" if st.session_state.get('browser_width', 1200) >= 768 else "Search:",
                value=initial_search_term,
                placeholder="Enter shape name or keywords...",
                key="search_term_input"
            )

        # History dropdown - directly in its own column
        with search_col2:
            if st.session_state.search_history:
                history_label = "📜 History" if st.session_state.get('browser_width', 1200) >= 768 else "📜"
                selected_history = st.selectbox(
                    history_label,
                    [""] + st.session_state.search_history,
                    index=0,
                    label_visibility="visible" if st.session_state.get('browser_width', 1200) >= 768 else "collapsed"
                )
                
                if selected_history and selected_history != search_term:
                    search_term = selected_history
                    st.rerun()
        
        # Save search button - directly in its own column
        with search_col3:
            # Add vertical space to align with other elements
            st.write("")
            save_search_btn = st.button("💾 Save", help="Save current search", use_container_width=True)
            
        # Improved save search form - outside of columns
        if save_search_btn and search_term:
            with st.form(key="save_search_form", clear_on_submit=True):
                st.subheader("Save Search")
                saved_search_name = st.text_input("Enter a name for this search:")
                
                form_col1, form_col2 = st.columns(2)
                submitted = form_col1.form_submit_button("Save", use_container_width=True)
                cancel = form_col2.form_submit_button("Cancel", use_container_width=True)
                
                if submitted and saved_search_name:
                    # Gather current filters
                    current_filters = {
                        'date_start': st.session_state.get('filter_date_start').isoformat() if st.session_state.get('filter_date_start') else None,
                        'date_end': st.session_state.get('filter_date_end').isoformat() if st.session_state.get('filter_date_end') else None,
                        'min_size': st.session_state.get('filter_min_size'),
                        'max_size': st.session_state.get('filter_max_size'),
                        'min_shapes': st.session_state.get('filter_min_shapes'),
                        'max_shapes': st.session_state.get('filter_max_shapes'),
                    }
                    # Add to DB
                    db = StencilDatabase()
                    success = db.add_saved_search(saved_search_name, search_term, current_filters)
                    db.close()
                    if success:
                        st.success(f"Search '{saved_search_name}' saved!")
                    else:
                        st.error(f"Failed to save search. Name might already exist.")
        elif save_search_btn and not search_term:
            st.warning("Please enter a search term before saving.")

        # Update stencils cache if button is clicked or directory changed
        if update_btn or st.session_state.last_scan_dir != root_dir:
            if not st.session_state.background_scan_running:
                # Start background scan
                scan_thread = threading.Thread(
                    target=background_scan,
                    args=(root_dir,),
                    daemon=True
                )
                scan_thread.start()
                
                # Show initial message
                st.info("Background scan started. You can continue searching while scanning updates.")
                time.sleep(0.1)  # Small delay to ensure thread starts
                st.rerun()  # Rerun to update UI
        
        # Display stats with improved layout and styling
        if st.session_state.stencils:
            total_shapes = sum(len(stencil.get('shapes', [])) for stencil in st.session_state.stencils)
            
            # Create a card-like container for stats
            with st.container(border=True):
                if st.session_state.get('browser_width', 1200) < 768:
                    # Two-column layout for mobile
                    stat_col1, stat_col2 = st.columns(2)
                    stat_col1.metric("📚 Stencils", len(st.session_state.stencils))
                    stat_col2.metric("🔷 Shapes", total_shapes)
                    st.metric("⭐ Favorites", len(st.session_state.favorite_stencils))
                else:
                    # Three-column layout for desktop
                    stat_col1, stat_col2, stat_col3 = st.columns(3)
                    stat_col1.metric("📚 Total Stencils", len(st.session_state.stencils))
                    stat_col2.metric("🔷 Total Shapes", total_shapes)
                    stat_col3.metric("⭐ Favorites", len(st.session_state.favorite_stencils))
        
        # About section with responsive layout - moved here for better visibility
        with st.expander("About Stencil Explorer"):
            is_mobile = st.session_state.get('browser_width', 1200) < 768
            app_version = config.get("app.version", "1.0.0")
            
            if is_mobile:
                # Simplified content for mobile
                st.markdown(f"""
                ### Visio Stencil Explorer v{app_version}
                
                This application helps find and manage Microsoft Visio shapes across multiple stencil files.
                
                #### Features:
                - Search across stencils
                - Preview shapes
                - Collect and export shapes
                - Create favorites
                - Import to Visio
                """)
            else:
                # Full content for larger screens
                col1, col2 = st.columns([3, 2])
                with col1:
                    st.markdown(f"""
                    ### Visio Stencil Explorer & Tools v{app_version}
                    
                    This application provides tools for working with Microsoft Visio files:
                    
                    1. **Stencil Explorer** (this page): Search for shapes across multiple Visio stencil files.
                    2. **Temp File Cleaner**: Find and remove corrupted Visio temporary files that can cause issues.
                    3. **Stencil Health**: Analyze stencils for issues such as duplicates or empty files.
                    
                    Select different tools from the sidebar navigation.
                    """)
                with col2:
                    st.markdown("""
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
        
        # Improved shape preview with better UI
        if st.session_state.preview_shape:
            with st.container(border=True):
                preview_col1, preview_col2 = st.columns([1, 3])
                with preview_col1:
                    # Generate and display shape preview
                    shape_preview = get_shape_preview(st.session_state.preview_shape)
                    st.image(shape_preview, width=150)
                
                with preview_col2:
                    st.subheader(f"{st.session_state.preview_shape}")
                    st.button("✖️ Close Preview", on_click=lambda: setattr(st.session_state, 'preview_shape', None))

    # Shape Collection Panel
    with collection_col:
        st.markdown("<h3 style='margin-bottom: 1rem;'>📋 Shape Collection</h3>", unsafe_allow_html=True)
        
        # Display collection count with better styling
        collection_count = len(st.session_state.shape_collection)
        
        # Collection stats in a card-like container
        with st.container(border=True):
            st.markdown(f"<div style='text-align: center;'><span style='font-size: 1.5rem; font-weight: bold;'>{collection_count}</span><br>shapes collected</div>", unsafe_allow_html=True)
            
            # Clear collection button with improved styling
            if collection_count > 0:
                st.button("🗑️ Clear Collection", on_click=clear_collection, use_container_width=True)
        
        # Display collected shapes with improved cards
        if collection_count > 0:
            for i, item in enumerate(st.session_state.shape_collection):
                with st.container(border=True):
                    # Ellipsis for long shape names
                    display_name = item['name']
                    if len(display_name) > 20:
                        display_name = display_name[:18] + "..."
                        
                    st.markdown(f"<p style='margin-bottom: 0.2rem; font-weight: bold;'>{display_name}</p>", unsafe_allow_html=True)
                    st.caption(f"From: {item['stencil_name']}")
                    
                    # Remove button with better positioning
                    st.button("❌ Remove", key=f"remove_{i}", 
                             help="Remove from collection", 
                             on_click=lambda i=i: remove_from_collection(i),
                             use_container_width=True)
            
            # Visio Integration Section
            st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)
            st.markdown("<h3 style='margin-bottom: 1rem;'>🔄 Import to Visio</h3>", unsafe_allow_html=True)
            
            # Check Visio availability with better styling
            if not visio.available:
                st.warning("Visio integration is not available. Install pywin32 to enable this feature.")
            else:
                # Status indicator with colored badge
                connection_status = "Connected" if st.session_state.visio_connected else "Not connected"
                status_color = "#28a745" if st.session_state.visio_connected else "#dc3545"
                status_icon = "✅" if st.session_state.visio_connected else "❌"
                
                st.markdown(f"""
                <div style='margin-bottom: 1rem;'>
                    <span style='font-weight: bold;'>Status:</span> 
                    <span style='background-color: {status_color}; color: white; padding: 0.2rem 0.5rem; border-radius: 3px;'>
                        {connection_status} {status_icon}
                    </span>
                </div>
                """, unsafe_allow_html=True)
                
                # Connect button with better styling
                st.button("🔄 Refresh Connection", 
                         on_click=refresh_visio_connection,
                         use_container_width=True)
                
                # Show open documents if connected
                if st.session_state.visio_connected:
                    if not st.session_state.visio_documents:
                        st.warning("No Visio documents open. Please open a document in Visio.")
                    else:
                        with st.container(border=True):
                            # Document selection with better styling
                            doc_options = [f"{doc['name']}" for doc in st.session_state.visio_documents]
                            selected_doc = st.selectbox(
                                "Select document:",
                                options=doc_options,
                                index=min(st.session_state.selected_doc_index - 1, len(doc_options) - 1)
                            )
                            selected_doc_index = doc_options.index(selected_doc) + 1
                            st.session_state.selected_doc_index = selected_doc_index
                            
                            # Get pages for selected document
                            pages = visio.get_pages_in_document(selected_doc_index)
                            
                            if not pages:
                                st.warning("No pages in selected document.")
                            else:
                                # Page selection
                                page_options = [f"{page['name']}" for page in pages]
                                selected_page = st.selectbox(
                                    "Select page:",
                                    options=page_options,
                                    index=min(st.session_state.selected_page_index - 1, len(page_options) - 1)
                                )
                                selected_page_index = page_options.index(selected_page) + 1
                                st.session_state.selected_page_index = selected_page_index
                                
                                # Import button with prominent styling
                                st.button("🚀 Import to Visio", 
                                         type="primary",
                                         on_click=lambda: import_collection_to_visio(
                                             selected_doc_index,
                                             selected_page_index
                                         ),
                                         use_container_width=True)
                else:
                    st.info("Connect to Visio to import shapes.")
        else:
            st.info("Click the ➕ button next to shapes in search results to add them to your collection.")
        
        # Favorites Section
        st.markdown("<hr style='margin: 1rem 0;'>", unsafe_allow_html=True)
        st.markdown("<h3 style='margin-bottom: 1rem;'>⭐ Favorites</h3>", unsafe_allow_html=True)
        
        # Favorites count with better styling
        fav_count = len(st.session_state.favorite_stencils)
        with st.container(border=True):
            st.markdown(f"<div style='text-align: center;'><span style='font-size: 1.5rem; font-weight: bold;'>{fav_count}</span><br>stencils bookmarked</div>", unsafe_allow_html=True)
        
        if fav_count > 0:
            # Display a compact list of favorite stencils
            for i, fav in enumerate(st.session_state.favorite_stencils):
                with st.container(border=True):
                    # Ellipsis for long stencil names
                    display_name = fav['name']
                    if len(display_name) > 20:
                        display_name = display_name[:18] + "..."
                        
                    st.markdown(f"<p style='margin-bottom: 0.2rem; font-weight: bold;'>{display_name}</p>", unsafe_allow_html=True)
                    
                    # View and Remove buttons as full-width buttons
                    st.button("👁️ View", 
                             key=f"sidebar_view_fav_{i}", 
                             help="View stencil shapes",
                             on_click=lambda i=i: view_favorite_stencil(i),
                             use_container_width=True)
                    
                    st.button("⭐ Remove", 
                             key=f"sidebar_unfav_{i}", 
                             help="Remove from favorites",
                             on_click=lambda fav=fav: toggle_favorite_stencil(fav["path"]),
                             use_container_width=True)
        else:
            st.info("Click the ☆ button next to shapes in search results to bookmark stencils.")

# Add a helper function for viewing favorite stencils
def view_favorite_stencil(index):
    """View a favorite stencil from the sidebar"""
    if 0 <= index < len(st.session_state.favorite_stencils):
        fav = st.session_state.favorite_stencils[index]
        # Find the stencil in the main list and show its shapes
        for stencil in st.session_state.stencils:
            if stencil["path"] == fav["path"]:
                st.session_state.selected_stencil = stencil
                st.session_state.show_favorites = False
                return True
    return False

if __name__ == "__main__":
    main() 