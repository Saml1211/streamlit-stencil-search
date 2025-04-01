import streamlit as st
import os
import glob
import subprocess
import sys
import platform
from pathlib import Path

# Add the project root directory to path so we can import from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import config, directory_preset_manager, visio
from app.core.db import StencilDatabase
from app.core.components import render_shared_sidebar

# Set page config - MUST be the first Streamlit command
st.set_page_config(
    page_title="Visio Temp File Cleaner",
    page_icon="🧹",
    layout="wide",
)

# Use the shared sidebar component
selected_directory = render_shared_sidebar(key_prefix="p2_")

def get_layout_columns():
    """Get column layout based on screen width"""
    # Get current browser width using JavaScript
    width = st.session_state.get('browser_width', 1200)  # Default to desktop
    
    if width < 768:  # Mobile
        return [1, 3, 4]  # Stack columns vertically on mobile
    elif width < 992:  # Tablet
        return [1, 3, 4]  # Slightly compressed
    else:  # Desktop
        return [1, 3, 5]  # Full width

def find_temp_files(directory):
    """Find Visio temp files in the specified directory recursively"""
    temp_files = []
    
    # Get patterns from config
    patterns = config.get("temp_cleaner.patterns", ["~$$*.*vssx"])
    
    # Check if we're on Windows (required for PowerShell)
    if platform.system() == "Windows":
        try:
            # Build pattern list for PowerShell
            pattern_condition = " -or ".join([f"$_.Name -like '{pattern}'" for pattern in patterns])
            
            # Use PowerShell to find the temp files (including hidden ones)
            ps_command = f'Get-ChildItem -Path "{directory}" -Recurse -Force -File | Where-Object {{ {pattern_condition} }} | Select-Object -ExpandProperty FullName'
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                check=True
            )
            files = result.stdout.strip().split("\n")
            # Filter out empty entries
            temp_files = [f for f in files if f.strip()]
        except subprocess.CalledProcessError as e:
            st.error(f"Error running PowerShell command: {e}")
            st.code(e.stderr)
    else:
        # Fallback for non-Windows systems using glob
        # Note: This may not find hidden files on all systems
        for pattern in patterns:
            glob_pattern = os.path.join(directory, "**", pattern)
            temp_files.extend(glob.glob(glob_pattern, recursive=True))
    
    return temp_files

def delete_file(file_path):
    """Delete a file with proper error handling"""
    try:
        os.remove(file_path)
        return True, f"Successfully deleted: {file_path}"
    except Exception as e:
        return False, f"Error deleting {file_path}: {str(e)}"

def main():
    # Window width tracking is now handled in app.py
    
    st.title("Visio Temporary File Cleaner")
    
    # Adjust description based on screen size
    if st.session_state.get('browser_width', 1200) < 768:
        st.markdown("Find and remove corrupted Visio temporary files.")
    else:
        st.markdown("""
        This tool helps find and remove corrupted Visio temporary files that can cause errors 
        in Microsoft Visio environments. These files match the pattern `~$$*.~vssx` and are 
        often hidden by default.
        """)
    
    # Use the directory from session state with a fallback
    if 'last_dir' in st.session_state:
        scan_dir = st.session_state.last_dir
    else:
        # Fallback to a default directory
        scan_dir = config.get("temp_cleaner.default_directory", "~/Documents")
        scan_dir = os.path.expanduser(scan_dir)
        # Store it in session state for next time
        st.session_state.last_dir = scan_dir

    # Input for directory to scan - responsive layout
    is_mobile = st.session_state.get('browser_width', 1200) < 768
    
    # Warning for non-Windows systems
    if platform.system() != "Windows":
        st.warning("⚠️ Full functionality requires Windows with PowerShell. Limited functionality available on other systems.")
    
    # Scan button
    scan_btn = st.button("🔍 Scan for Temp Files", use_container_width=is_mobile, key="temp_cleaner_scan_btn")
    
    # Handle scanning
    if scan_btn:
        if not os.path.exists(scan_dir):
            st.error(f"Directory does not exist: {scan_dir}")
        else:
            with st.spinner("Scanning for Visio temporary files..."):
                temp_files = find_temp_files(scan_dir)
                
                # Store in session state for persistence
                st.session_state.temp_files = temp_files
    
    # Display results if available
    if 'temp_files' in st.session_state and st.session_state.temp_files:
        temp_files = st.session_state.temp_files
        
        st.success(f"Found {len(temp_files)} temporary Visio file(s)")
        
        # Create a DataFrame for better display
        files_data = []
        for idx, file_path in enumerate(temp_files):
            file_name = os.path.basename(file_path)
            dir_name = os.path.dirname(file_path)
            files_data.append({
                "select": True,
                "index": idx,
                "name": file_name,
                "directory": dir_name,
                "full_path": file_path
            })
        
        # Allow selecting files to delete
        st.write("Select files to delete:")
        
        # Get responsive column layout
        column_sizes = get_layout_columns()
        
        # Create columns for the table header
        col1, col2, col3 = st.columns(column_sizes)
        col1.markdown("**Select**")
        col2.markdown("**File Name**")
        col3.markdown("**Directory**")
        
        # Create checkboxes for each file
        selected_files = []
        for file_data in files_data:
            col1, col2, col3 = st.columns(column_sizes)
            
            # Checkbox for selection
            is_selected = col1.checkbox("", value=True, key=f"file_{file_data['index']}")
            
            # Responsive display
            if is_mobile:
                col2.markdown(f"**{file_data['name']}**")
                col3.markdown(f"*{file_data['directory']}*")
            else:
                col2.text(file_data["name"])
                col3.text(file_data["directory"])
            
            if is_selected:
                selected_files.append(file_data["full_path"])
        
        # Delete button
        if selected_files:
            btn_label = f"🗑️ Delete {len(selected_files)}" if is_mobile else f"🗑️ Delete {len(selected_files)} Selected File(s)"
            if st.button(btn_label, type="primary", use_container_width=is_mobile):
                results = []
                success_count = 0
                
                # Process deletions with a progress bar
                progress_bar = st.progress(0)
                for i, file_path in enumerate(selected_files):
                    success, message = delete_file(file_path)
                    results.append(message)
                    if success:
                        success_count += 1
                    progress_bar.progress((i + 1) / len(selected_files))
                
                # Show results
                if success_count > 0:
                    st.success(f"Deleted {success_count} of {len(selected_files)} files")
                
                if success_count < len(selected_files):
                    st.error(f"Failed to delete {len(selected_files) - success_count} files")
                
                with st.expander("Detailed Results"):
                    for result in results:
                        st.text(result)
                
                # Reset the session state to refresh the list
                if 'temp_files' in st.session_state:
                    # Remove the successfully deleted files from the list
                    st.session_state.temp_files = [
                        f for f in st.session_state.temp_files 
                        if f in selected_files and not os.path.exists(f)
                    ]
                
                # Force a rerun to update the UI
                st.rerun()
        else:
            st.info("No files selected for deletion")
    
    elif 'temp_files' in st.session_state and not st.session_state.temp_files:
        st.info("No Visio temporary files found in the specified directory")
    
    # Information section
    with st.expander("About Visio Temporary Files"):
        if is_mobile:
            # Simplified content for mobile
            st.markdown("""
            ### What are these files?
            
            Visio creates temporary files during editing that should be cleaned up when Visio closes. 
            When Visio crashes, these temp files remain and can cause corruption.
            
            ### Why remove them?
            
            These files can cause errors, corruption, and conflicts with newer versions.
            """)
        else:
            # Full content for larger screens
            st.markdown("""
            ### What are these files?
            
            Visio creates temporary files (patterns like `~$$*.~vssx`) during editing. Normally, these 
            are cleaned up when Visio closes properly. However, if Visio crashes or closes unexpectedly,
            these files can remain and cause corruption in Visio shapes and templates.
            
            ### Why are they problematic?
            
            These leftover temporary files can:
            - Cause errors when opening Visio documents
            - Lead to corruption in Visio shapes and stencils
            - Create conflicts with newer versions of the same files
            
            ### How this tool helps
            
            This tool scans for these problematic temporary files and allows you to safely remove them,
            which can resolve many common Visio errors.
            """)

# Call main() only once using if/else pattern
if __name__ == "__main__":
    main()
else:
    main() 