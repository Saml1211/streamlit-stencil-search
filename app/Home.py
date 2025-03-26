import streamlit as st
import os
import sys

# Add the parent directory to path so we can import from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set page config
st.set_page_config(
    page_title="Visio Stencil Search",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

def main():
    st.title("Visio Stencil Explorer")
    
    # Configuration
    st.sidebar.header("Settings")
    root_dir = st.sidebar.text_input("Stencil Directory", 
                                   value="Z:/ENGINEERING TEMPLATES/VISIO SHAPES 2025")
    update_btn = st.sidebar.button("🔁 Update Database")
    
    # Search functionality
    search_term = st.text_input("Search shapes:", placeholder="Enter shape name...")
    
    # Placeholder for functionality
    st.info("🚧 This application is under development. Core functionality coming soon.")
    
    # Placeholder for results
    if search_term:
        st.write(f"Searching for: {search_term}")
        
        # Example results layout
        col1, col2, col3 = st.columns([3, 2, 3])
        with col1:
            st.markdown("**Shape Name**")
        with col2:
            st.markdown("**Stencil**")
        with col3: 
            st.markdown("**Location**")
        
        with st.container(border=True):
            cols = st.columns([3, 2, 3])
            cols[0].write("Example Shape")
            cols[1].write("Example.vssx")
            cols[2].code("Z:/Example/Path/Example.vssx")

if __name__ == "__main__":
    main() 