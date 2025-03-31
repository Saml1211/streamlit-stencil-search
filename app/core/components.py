import os
import streamlit as st
from typing import Optional, Dict, List
from .db import StencilDatabase
from .config import config

def directory_preset_manager(container=st.sidebar, key_prefix="") -> str:
    """
    Render a directory preset manager component in the given container.
    This component allows users to select from preset directories and
    save new presets.
    
    Args:
        container: Streamlit container to render the component in (default: st.sidebar)
        key_prefix: Prefix to add to all keys to ensure uniqueness (default: "")
        
    Returns:
        str: The currently selected directory path
    """
    # Add a header
    container.markdown("<h3>Stencil Directory</h3>", unsafe_allow_html=True)
    
    # Get active directory and preset from the database
    db = StencilDatabase()
    active_dir = db.get_active_directory()
    preset_dirs = db.get_preset_directories()
    
    # Determine the default directory
    if active_dir:
        default_dir = active_dir['path']
    else:
        default_dir = config.get("paths.stencil_directory", "./test_data")
        if not os.path.exists(default_dir):
            default_dir = "./test_data" if os.path.exists("./test_data") else "Z:/ENGINEERING TEMPLATES/VISIO SHAPES 2025"
    
    # Check if we're on mobile based on browser width (if available)
    is_mobile = st.session_state.get('browser_width', 1200) < 768
    
    if is_mobile:
        # Mobile layout
        dir_col1, dir_col2 = container.columns([4, 1])
        with dir_col1:
            # Preset selector for mobile
            if preset_dirs:
                preset_options = {d['name']: d for d in preset_dirs}
                selected_preset = container.selectbox(
                    "Preset Directories",
                    ["-- Select Preset --"] + list(preset_options.keys()),
                    index=0,
                    key=f"{key_prefix}preset_selector_mobile"
                )
                
                if selected_preset != "-- Select Preset --":
                    selected_dir = preset_options[selected_preset]
                    if not selected_dir['is_active']:
                        db.set_active_directory(selected_dir['id'])
                        # Rerun to reflect changed directory
                        st.rerun()
            
            # Directory input
            directory = container.text_input(
                "Directory:", 
                value=default_dir,
                key=f"{key_prefix}dir_input_mobile"
            )
    else:
        # Desktop layout
        # Preset directory selector
        if preset_dirs:
            preset_options = {d['name']: d for d in preset_dirs}
            selected_preset = container.selectbox(
                "Preset Directories",
                ["-- Select Preset --"] + list(preset_options.keys()),
                index=0,
                key=f"{key_prefix}preset_selector_desktop"
            )
            
            if selected_preset != "-- Select Preset --":
                selected_dir = preset_options[selected_preset]
                if not selected_dir['is_active']:
                    db.set_active_directory(selected_dir['id'])
                    # Rerun to reflect changed directory
                    st.rerun()
        
        # Directory input
        directory = container.text_input(
            "Stencil Directory", 
            value=default_dir,
            key=f"{key_prefix}dir_input_desktop"
        )
        
        # Save as preset button
        save_preset_btn = container.button("💾 Save as Preset", use_container_width=True, key=f"{key_prefix}save_preset_btn")
        if save_preset_btn:
            with container.form(key=f"{key_prefix}save_preset_form", clear_on_submit=True):
                st.subheader("Save Directory Preset")
                preset_name = st.text_input("Enter a name for this preset:", key=f"{key_prefix}preset_name_input")
                
                form_col1, form_col2 = st.columns(2)
                submitted = form_col1.form_submit_button("Save", use_container_width=True)
                cancel = form_col2.form_submit_button("Cancel", use_container_width=True)
                
                if submitted and preset_name:
                    success = db.add_preset_directory(directory, preset_name)
                    if success:
                        st.success(f"Preset '{preset_name}' saved!")
                        st.rerun()
                    else:
                        st.error("Failed to save preset. Directory might already exist.")
    
    # Update active directory in database when changed
    if 'last_dir' not in st.session_state or st.session_state.last_dir != directory:
        st.session_state.last_dir = directory
        # Add and set as active if not already in presets
        db.add_preset_directory(directory)
        # Get the directory ID and set it as active
        preset_dirs = db.get_preset_directories()
        for preset in preset_dirs:
            if preset['path'] == directory:
                db.set_active_directory(preset['id'])
                break
    
    db.close()
    return directory 