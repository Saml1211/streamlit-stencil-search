import streamlit as st
import os
import sys

# Add the parent directory to path so we can import from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import scan_directory, parse_visio_stencil

# Set page config
st.set_page_config(
    page_title="Visio Stencil Search",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state for stencils cache
if 'stencils' not in st.session_state:
    st.session_state.stencils = []
    st.session_state.last_scan_dir = ""

def main():
    st.title("Visio Stencil Explorer")
    
    # Configuration
    st.sidebar.header("Settings")
    root_dir = st.sidebar.text_input("Stencil Directory", 
                                   value="./test_data" if os.path.exists("./test_data") else "Z:/ENGINEERING TEMPLATES/VISIO SHAPES 2025")
    update_btn = st.sidebar.button("🔁 Update Database")
    
    # Search functionality
    search_term = st.text_input("Search shapes:", placeholder="Enter shape name...")
    
    # Update stencils cache if button is clicked or directory changed
    if update_btn or st.session_state.last_scan_dir != root_dir:
        with st.spinner("Scanning stencil files..."):
            try:
                st.session_state.stencils = scan_directory(root_dir, parse_visio_stencil)
                st.session_state.last_scan_dir = root_dir
                st.success(f"Found {len(st.session_state.stencils)} stencil files")
            except Exception as e:
                st.error(f"Error scanning directory: {str(e)}")
    
    # Display stats
    if st.session_state.stencils:
        total_shapes = sum(len(stencil.get('shapes', [])) for stencil in st.session_state.stencils)
        col1, col2 = st.columns(2)
        col1.metric("Total Stencils", len(st.session_state.stencils))
        col2.metric("Total Shapes", total_shapes)
    
    # Search and display results
    if st.session_state.stencils:
        if search_term:
            st.write(f"Searching for: {search_term}")
            
            # Setup results columns
            col1, col2, col3 = st.columns([3, 2, 3])
            with col1:
                st.markdown("**Shape Name**")
            with col2:
                st.markdown("**Stencil**")
            with col3: 
                st.markdown("**Location**")
            
            # Filter and display results
            results_found = False
            for stencil in st.session_state.stencils:
                matches = [shape for shape in stencil.get('shapes', []) 
                          if search_term.lower() in shape.lower()]
                
                for shape in matches:
                    results_found = True
                    with st.container(border=True):
                        cols = st.columns([3, 2, 3])
                        cols[0].write(shape)
                        cols[1].write(stencil['name'])
                        cols[2].code(stencil['path'])
            
            if not results_found:
                st.info("No matching shapes found. Try a different search term.")
        else:
            st.info("👆 Enter a search term above to find shapes.")
    else:
        st.info("🚧 No stencils loaded. Click 'Update Database' to scan for stencils.")

if __name__ == "__main__":
    main() 