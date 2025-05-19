import os
import streamlit as st
from typing import Optional, Dict, List
from .db import StencilDatabase
from .config import config
from . import visio
from pathlib import Path

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
    # Prioritize last used valid directory from session state
    last_dir_from_session = st.session_state.get('last_dir')
    if last_dir_from_session and os.path.isdir(last_dir_from_session):
        default_dir = last_dir_from_session
    elif active_dir:
        default_dir = active_dir['path']
    else:
        default_dir = config.get("paths.stencil_directory", "./test_data")
        if not os.path.exists(default_dir):
            default_dir = "./test_data" if os.path.exists("./test_data") else "Z:/ENGINEERING TEMPLATES/VISIO SHAPES 2025"

    # Check if we're on mobile based on browser width (if available)
    is_mobile = st.session_state.get('browser_width', 1200) < 768

    # Prepare preset options
    preset_options_list = db.get_preset_directories() # Fetch fresh list
    preset_map = {p['name']: p for p in preset_options_list}
    preset_names = list(preset_map.keys())

    # Determine the initial index for the selectbox based on the active directory
    active_preset_name = None
    if active_dir:
        active_preset_name = active_dir['name']
    elif last_dir_from_session:
         # If last_dir exists but no active preset, find its name if it's a preset
         for p in preset_options_list:
             if p['path'] == last_dir_from_session:
                 active_preset_name = p['name']
                 break

    initial_preset_index = 0
    if active_preset_name and active_preset_name in preset_names:
        initial_preset_index = preset_names.index(active_preset_name) + 1 # +1 for "-- Select Preset --"

    if is_mobile:
        # Mobile layout
        dir_col1, dir_col2 = container.columns([4, 1])
        with dir_col1:
            # Preset selector for mobile
            preset_options = {d['name']: d for d in preset_dirs} if preset_dirs else {}
            selected_preset = container.selectbox(
                "Preset Directories",
                ["-- Select Preset --"] + list(preset_options.keys()),
                index=0,
                key=f"{key_prefix}preset_selector_mobile"
            )

            if selected_preset != "-- Select Preset --" and preset_dirs:
                selected_dir = preset_options[selected_preset]
                if not active_dir or selected_dir['id'] != active_dir['id']:
                    db.set_active_directory(selected_dir['id'])
                    st.session_state.last_dir = selected_dir['path'] # Update session state
                    st.rerun()

            # Directory input
            directory = container.text_input(
                "Directory:",
                value=st.session_state.get('last_dir', default_dir), # Use session state
                key=f"{key_prefix}dir_input_mobile"
            )
    else:
        # Desktop layout
        # Preset directory selector
        preset_options = {d['name']: d for d in preset_dirs} if preset_dirs else {}
        preset_names = list(preset_options.keys())
        current_preset_name = "-- Select Preset --"
        if active_dir and active_dir['name'] in preset_map:
            current_preset_name = active_dir['name']
        elif last_dir_from_session:
             for name, data in preset_map.items():
                 if data['path'] == last_dir_from_session:
                     current_preset_name = name
                     break
        
        current_preset_index = 0
        if current_preset_name != "-- Select Preset --":
            current_preset_index = preset_names.index(current_preset_name) + 1
        
        selected_preset = container.selectbox(
            "Preset Directories",
            ["-- Select Preset --"] + preset_names,
            index=current_preset_index, # Set initial index correctly
            key=f"{key_prefix}preset_selector_desktop"
        )

        # Update based on selectbox change
        if selected_preset != "-- Select Preset --":
            selected_preset_data = preset_map[selected_preset]
            # Check if selection actually changed the active dir
            if not active_dir or selected_preset_data['id'] != active_dir['id']:
                db.set_active_directory(selected_preset_data['id'])
                st.session_state.last_dir = selected_preset_data['path'] # Update session state
                st.rerun()
            # Ensure directory value matches selection
            directory_value = selected_preset_data['path']
        else:
            # If no preset selected, use session state or default
            directory_value = st.session_state.get('last_dir', default_dir)

        # Directory input
        directory = container.text_input(
            "Stencil Directory",
            value=directory_value, # Use derived value
            key=f"{key_prefix}dir_input_desktop"
        )

        # Save as preset button and Set Active button
        col1, col2 = container.columns(2)
        save_preset_btn = col1.button("💾 Save as Preset", use_container_width=True, key=f"{key_prefix}save_preset_btn")
        set_active_btn = col2.button("📌 Set Active Directory", use_container_width=True, key=f"{key_prefix}set_active_btn")

        if save_preset_btn:
            with container.form(key=f"{key_prefix}save_preset_form", clear_on_submit=True):
                st.subheader("Save Directory Preset")
                preset_name_input = st.text_input("Enter a name for this preset:", key=f"{key_prefix}preset_name_input")
                form_col1, form_col2 = st.columns(2)
                submitted = form_col1.form_submit_button("Save", use_container_width=True)
                cancel = form_col2.form_submit_button("Cancel", use_container_width=True)
                if submitted and preset_name_input:
                    path_to_save = directory # Use current text input value
                    if os.path.isdir(path_to_save):
                        save_success = db.add_preset_directory(path_to_save, preset_name_input)
                        if save_success:
                            st.success(f"Preset '{preset_name_input}' saved!")
                            # Automatically set active?
                            # preset_id = db.get_preset_by_path(path_to_save) # Need this helper
                            # if preset_id: db.set_active_directory(preset_id)
                            st.rerun()
                        else:
                            st.error("Failed to save preset. Directory or name might already exist.")
                    else:
                        st.error(f"Invalid directory path: {path_to_save}")

        # Handle Set Active button click
        if set_active_btn:
            if os.path.isdir(directory):
                # Find or add preset and get its ID
                target_id = None
                existing_presets = db.get_preset_directories()
                for p in existing_presets:
                    if p['path'] == directory:
                        target_id = p['id']
                        break
                if not target_id:
                    # Try adding it if it doesn't exist as a preset yet
                    preset_name = Path(directory).name
                    if db.add_preset_directory(directory, preset_name):
                         # Need to get the ID after adding
                         added_presets = db.get_preset_directories()
                         for p in added_presets:
                             if p['path'] == directory:
                                 target_id = p['id']
                                 break
                    else:
                        st.error("Failed to add directory as a new preset.")
                
                # Set active if we have an ID
                if target_id:
                    if db.set_active_directory(target_id):
                        st.success(f"Directory '{directory}' set as active.")
                        st.session_state.last_dir = directory
                        st.rerun()
                    else:
                        st.error("Failed to set directory as active in DB.")
                # No else needed, errors handled above
            else:
                st.error(f"Directory path is not valid: {directory}")

    if directory != st.session_state.get('last_dir'):
        if os.path.isdir(directory):
            st.session_state.last_dir = directory
            # Don't automatically set active here; require button or preset select
        else:
            pass # Ignore invalid manual input for now

    db.close()
    # Return the directory currently shown in the text input
    return directory

def render_shared_sidebar(key_prefix="") -> str:
    """
    Render the shared sidebar components including directory preset manager
    and Visio integration status.

    Args:
        key_prefix: Prefix to add to all keys to ensure uniqueness (default: "")

    Returns:
        str: The currently selected directory path
    """
    with st.sidebar:
        # Directory preset manager
        st.markdown("<h3>Settings</h3>", unsafe_allow_html=True)
        # selected_directory = directory_preset_manager(key_prefix=key_prefix) # Temporarily commented out
        selected_directory = "." # Temporarily hardcoded for testing
        st.sidebar.caption("Directory manager temporarily disabled for testing.") # Add a note

        # Add Visio integration section
        st.markdown("<h3>Visio Integration</h3>", unsafe_allow_html=True)

        # Connection settings
        with st.expander("Connection Settings", expanded=False):
            # Initialize connection settings in session state if not present
            if 'visio_connection_type' not in st.session_state:
                st.session_state.visio_connection_type = "local"
            if 'visio_server_name' not in st.session_state:
                st.session_state.visio_server_name = ""

            # Connection type selector
            connection_type = st.radio(
                "Connection Type",
                options=["Local", "Remote"],
                index=0 if st.session_state.visio_connection_type == "local" else 1,
                key=f"{key_prefix}connection_type"
            )
            st.session_state.visio_connection_type = connection_type.lower()

            # Server name input for remote connections
            if st.session_state.visio_connection_type == "remote":
                server_name = st.text_input(
                    "Server Name",
                    value=st.session_state.visio_server_name,
                    help="Enter the name or IP address of the remote computer running Visio",
                    key=f"{key_prefix}server_name"
                )
                st.session_state.visio_server_name = server_name

                st.info(
                    "Note: The remote computer must have DCOM configured to allow remote connections " +
                    "to Visio. Use dcomcnfg.exe on the remote computer to configure DCOM settings."
                )

        # Connection status and refresh button
        visio_status_col1, visio_status_col2 = st.columns([3, 1])

        with visio_status_col2:
            refresh_btn = st.button("🔄", key=f"{key_prefix}refresh_visio_btn")

        # Temporarily disable automatic connection for testing
        if refresh_btn: # Only attempt connection if refresh is explicitly clicked
            server_name = None
            if st.session_state.visio_connection_type == "remote" and st.session_state.visio_server_name:
                server_name = st.session_state.visio_server_name

            # Only connect if refresh is clicked
            st.session_state.visio_connected = visio.connect(server_name)

            if st.session_state.visio_connected:
                st.session_state.visio_documents = visio.get_open_documents()
                doc_index, page_index, found_valid = visio.get_default_document_page()
                if found_valid:
                    st.session_state.selected_doc_index = doc_index
                    st.session_state.selected_page_index = page_index
            # else: # Ensure documents list is empty if not connected
            #    st.session_state.visio_documents = []

        with visio_status_col1:
            if st.session_state.get('visio_connected', False):
                connection_type = "Remote" if visio.server_name else "Local"
                server_info = f" ({visio.server_name})" if visio.server_name else ""

                if st.session_state.get('visio_documents', []):
                    st.success(f"{connection_type} Visio{server_info}: {len(st.session_state.visio_documents)} doc(s)")
                else:
                    st.warning(f"{connection_type} Visio{server_info}: No documents open")
            else:
                st.error("Visio not connected")
                st.caption("Click 🔄 to connect") # Added caption

        # Add a separator
        st.markdown("---")

        return selected_directory