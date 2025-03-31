import os
import streamlit as st
from config import config
from database.stencil_database import StencilDatabase

with main_col:
    # Configuration in sidebar
    st.sidebar.markdown("<h3>Settings</h3>", unsafe_allow_html=True)
    
    # Directory Management
    st.sidebar.markdown("<h4>Stencil Directory</h4>", unsafe_allow_html=True)
    
    # Get active directory or default from config
    db = StencilDatabase()
    active_dir = db.get_active_directory()
    preset_dirs = db.get_preset_directories()
    
    if active_dir:
        default_dir = active_dir['path']
    else:
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
        # Preset directory selector
        if preset_dirs:
            preset_options = {d['name']: d for d in preset_dirs}
            selected_preset = st.sidebar.selectbox(
                "Preset Directories",
                ["-- Select Preset --"] + list(preset_options.keys()),
                index=0,
                key="preset_selector"
            )
            
            if selected_preset != "-- Select Preset --":
                selected_dir = preset_options[selected_preset]
                if not selected_dir['is_active']:
                    db.set_active_directory(selected_dir['id'])
                    st.rerun()
        
        # Directory input
        root_dir = st.sidebar.text_input("Stencil Directory", 
                                      value=default_dir, key="dir_input_large")
        
        # Save as preset button
        save_preset_btn = st.sidebar.button("💾 Save as Preset", use_container_width=True)
        if save_preset_btn:
            with st.sidebar.form(key="save_preset_form", clear_on_submit=True):
                st.subheader("Save Directory Preset")
                preset_name = st.text_input("Enter a name for this preset:")
                
                form_col1, form_col2 = st.columns(2)
                submitted = form_col1.form_submit_button("Save", use_container_width=True)
                cancel = form_col2.form_submit_button("Cancel", use_container_width=True)
                
                if submitted and preset_name:
                    success = db.add_preset_directory(root_dir, preset_name)
                    if success:
                        st.success(f"Preset '{preset_name}' saved!")
                        st.rerun()
                    else:
                        st.error("Failed to save preset. Directory might already exist.")
        
        # Update and auto-refresh controls
        update_col1, update_col2 = st.sidebar.columns([1, 1])
        with update_col1:
            update_btn = st.button("🔄 Update Now", use_container_width=True, key="update_btn_large")
        with update_col2:
            # Auto-refresh toggle and interval from config
            auto_refresh_interval = config.get("scanner.auto_refresh_interval", 1)
            auto_refresh = st.checkbox("Auto Refresh", value=(auto_refresh_interval > 0),
                                      help=f"Refresh every {auto_refresh_interval} hour(s)", key="auto_refresh")
    
    # Update active directory in database when changed
    if 'last_dir' not in st.session_state or st.session_state.last_dir != root_dir:
        st.session_state.last_dir = root_dir
        # Add and set as active if not already in presets
        db.add_preset_directory(root_dir)
        # Get the directory ID and set it as active
        preset_dirs = db.get_preset_directories()
        for preset in preset_dirs:
            if preset['path'] == root_dir:
                db.set_active_directory(preset['id'])
                break
    
    db.close()
    
    # Advanced Search Filters in sidebar 