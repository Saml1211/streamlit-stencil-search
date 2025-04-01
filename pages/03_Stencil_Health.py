import streamlit as st
import os
import sys
import pandas as pd
from collections import Counter
from datetime import datetime
import time
import io
import matplotlib.pyplot as plt
import numpy as np
import re
import threading

# Add the project root directory to path so we can import from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import scan_directory, parse_visio_stencil, config, get_shape_preview, directory_preset_manager, visio
from app.core.db import StencilDatabase
from app.core.components import render_shared_sidebar

# Set page config - MUST be the first Streamlit command
st.set_page_config(
    page_title="Stencil Health Monitor",
    page_icon="🧪",
    layout="wide",
)

# Use the shared sidebar component
selected_directory = render_shared_sidebar(key_prefix="p3_")

# Initialize session state for cache
if 'health_scan_running' not in st.session_state:
    st.session_state.health_scan_running = False
if 'health_data' not in st.session_state:
    st.session_state.health_data = None
if 'health_scan_progress' not in st.session_state:
    st.session_state.health_scan_progress = 0
if 'preview_shape' not in st.session_state:
    st.session_state.preview_shape = None

def analyze_stencil_health(root_dir):
    """
    Analyze stencil health by checking for:
    - Empty stencils (no shapes)
    - Duplicate shapes within stencils
    - Multiple versions of the same stencil
    - Unusually large stencils
    - Potentially corrupt stencils
    """
    # Get severity thresholds from config
    thresholds = config.get("health.thresholds", {"low": 1, "medium": 5, "high": 10})
    
    # Start with cached data if available
    db = StencilDatabase()
    stencils = db.get_cached_stencils()
    
    # If no cached data, scan directory
    if not stencils:
        stencils = scan_directory(root_dir, parse_visio_stencil, use_cache=True)
    
    # Update progress for UI feedback
    st.session_state.health_scan_progress = 10
    time.sleep(0.1)  # Give UI time to update
    
    # Analyze empty stencils
    empty_stencils = []
    for stencil in stencils:
        if stencil['shape_count'] == 0:
            empty_stencils.append({
                'path': stencil['path'],
                'name': stencil['name'],
                'issue': 'Empty stencil (no shapes)',
                'severity': 'Medium'
            })
    
    st.session_state.health_scan_progress = 30
    time.sleep(0.1)  # Give UI time to update
    
    # Analyze duplicate shapes within stencils
    duplicate_shapes = []
    for stencil in stencils:
        shape_counts = Counter(stencil['shapes'])
        for shape, count in shape_counts.items():
            if count > 1:
                duplicate_shapes.append({
                    'path': stencil['path'],
                    'name': stencil['name'],
                    'issue': f'Duplicate shape: "{shape}" appears {count} times',
                    'severity': 'Low' if count < thresholds.get('medium', 5) else 'Medium',
                    'shape': shape  # Store the shape name for preview
                })
    
    st.session_state.health_scan_progress = 50
    time.sleep(0.1)  # Give UI time to update
    
    # Check for unusually large stencils (by shape count)
    large_stencils = []
    shape_counts = [stencil['shape_count'] for stencil in stencils if stencil['shape_count'] > 0]
    if shape_counts:
        mean_shape_count = sum(shape_counts) / len(shape_counts)
        std_shape_count = np.std(shape_counts)
        threshold = mean_shape_count + (2 * std_shape_count)  # 2 standard deviations above mean
        
        for stencil in stencils:
            if stencil['shape_count'] > threshold and stencil['shape_count'] > 20:  # Minimum of 20 shapes to be flagged
                large_stencils.append({
                    'path': stencil['path'],
                    'name': stencil['name'],
                    'issue': f'Unusually large stencil: {stencil["shape_count"]} shapes (average is {int(mean_shape_count)})',
                    'severity': 'Medium',
                    'shapes': stencil['shapes']  # Store all shapes for potential preview
                })
    
    st.session_state.health_scan_progress = 60
    time.sleep(0.1)  # Give UI time to update
    
    # Check for potentially corrupt stencils (incomplete parsing)
    corrupt_stencils = []
    for stencil in stencils:
        # If shapes list contains any placeholder error messages from the parser
        for shape in stencil.get('shapes', []):
            if '[Binary format not supported:' in shape or 'Error parsing' in shape:
                corrupt_stencils.append({
                    'path': stencil['path'],
                    'name': stencil['name'],
                    'issue': 'Potentially corrupt or unsupported format',
                    'severity': 'High'
                })
                break
    
    st.session_state.health_scan_progress = 70
    time.sleep(0.1)  # Give UI time to update
    
    # Analyze stencil name variants (possible duplicates)
    stencil_name_map = {}
    for stencil in stencils:
        base_name = stencil['name'].lower().replace('_', ' ').strip()
        if base_name not in stencil_name_map:
            stencil_name_map[base_name] = []
        stencil_name_map[base_name].append(stencil)
    
    # Find stencils with multiple versions
    version_issues = []
    for name, stencil_list in stencil_name_map.items():
        if len(stencil_list) > 1:
            for stencil in stencil_list:
                # Assign severity based on the number of duplicates
                severity = 'Low'
                if len(stencil_list) >= thresholds.get('high', 10):
                    severity = 'High'
                elif len(stencil_list) >= thresholds.get('medium', 5):
                    severity = 'Medium'
                
                version_issues.append({
                    'path': stencil['path'],
                    'name': stencil['name'],
                    'issue': f'Multiple versions exist: Found {len(stencil_list)} stencils with similar names',
                    'severity': severity,
                    'shapes': stencil['shapes']  # Store shapes for preview
                })
    
    st.session_state.health_scan_progress = 100
    
    # Combine all issues
    all_issues = empty_stencils + duplicate_shapes + large_stencils + corrupt_stencils + version_issues
    
    # Create a summary of the scan
    summary = {
        'scan_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_stencils': len(stencils),
        'total_issues': len(all_issues),
        'empty_stencils': len(empty_stencils),
        'large_stencils': len(large_stencils),
        'corrupt_stencils': len(corrupt_stencils),
        'stencils_with_duplicates': len(set(d['path'] for d in duplicate_shapes)),
        'version_conflicts': len(set(d['path'] for d in version_issues))
    }
    
    return {
        'issues': all_issues,
        'summary': summary,
        'stencils': stencils
    }

def export_to_csv(data):
    """Export issues to CSV"""
    df = pd.DataFrame(data['issues'])
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()

def export_to_excel(data):
    """Export full health report to Excel"""
    # Create a Pandas Excel writer
    output = io.BytesIO()
    
    # Create DataFrames
    issues_df = pd.DataFrame(data['issues'])
    summary_df = pd.DataFrame([data['summary']])
    stencils_df = pd.DataFrame([{
        'path': s['path'],
        'name': s['name'],
        'shape_count': s['shape_count'],
        'extension': s['extension'],
        'last_scan': s.get('last_scan', '')
    } for s in data['stencils']])
    
    # Write each dataframe to a different worksheet
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        issues_df.to_excel(writer, sheet_name='Issues', index=False)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        stencils_df.to_excel(writer, sheet_name='All Stencils', index=False)
    
    return output.getvalue()

def generate_health_charts(data):
    """Generate charts for health analysis visualization"""
    summary = data['summary']
    issues = data['issues']
    
    # Count issues by severity
    severity_counts = Counter([issue['severity'] for issue in issues])
    
    # Create a Matplotlib figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    
    # Plot 1: Issues by Type
    issue_types = {
        'Empty Stencils': summary['empty_stencils'],
        'Large Stencils': summary['large_stencils'],
        'Corrupt Stencils': summary['corrupt_stencils'],
        'Duplicate Shapes': summary['stencils_with_duplicates'],
        'Version Conflicts': summary['version_conflicts']
    }
    
    # Remove zero values
    issue_types = {k: v for k, v in issue_types.items() if v > 0}
    
    if issue_types:
        ax1.bar(issue_types.keys(), issue_types.values(), color='skyblue')
        ax1.set_title('Issues by Type')
        ax1.tick_params(axis='x', rotation=45)
        ax1.set_ylabel('Count')
    else:
        ax1.text(0.5, 0.5, 'No issues found', ha='center', va='center', fontsize=12)
        ax1.set_title('Issues by Type')
    
    # Plot 2: Issues by Severity
    severity_order = ['High', 'Medium', 'Low']
    severity_data = [severity_counts.get(s, 0) for s in severity_order]
    colors = ['red', 'orange', 'green']
    
    if sum(severity_data) > 0:
        ax2.pie(severity_data, labels=severity_order, colors=colors, autopct='%1.1f%%', startangle=90)
        ax2.set_title('Issues by Severity')
    else:
        ax2.text(0.5, 0.5, 'No issues found', ha='center', va='center', fontsize=12)
        ax2.set_title('Issues by Severity')
    
    plt.tight_layout()
    
    # Convert plot to image
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    plt.close(fig)
    
    return buf

def background_health_scan(root_dir):
    """Run health scan in background thread"""
    def run_scan():
        try:
            # Analyze stencil health
            health_data = analyze_stencil_health(root_dir)
            # Store results in session state
            st.session_state.health_data = health_data
        except Exception as e:
            st.error(f"Error during health scan: {str(e)}")
        finally:
            # Mark scan as complete
            st.session_state.health_scan_running = False
    
    # Set scan as running
    st.session_state.health_scan_running = True
    st.session_state.health_scan_progress = 0
    
    # Start scan in background thread
    thread = threading.Thread(target=run_scan)
    thread.start()

def toggle_shape_preview(shape=None):
    """Toggle shape preview in session state"""
    st.session_state.preview_shape = shape

def main():
    # Window width tracking is now handled in app.py
    
    st.title("Stencil Health Monitor")
    
    # Use responsive layout based on screen size
    is_mobile = st.session_state.get('browser_width', 1200) < 768
    
    # Page description
    if is_mobile:
        st.markdown("Analyze your stencil files for health issues.")
    else:
        st.markdown("""
        This tool analyzes your Visio stencil files for health issues such as empty stencils,
        duplicate shapes, multiple versions, and potential corruption.
        """)
    
    # Use the directory from session state with a fallback
    if 'last_dir' in st.session_state:
        root_dir = st.session_state.last_dir
    else:
        # Fallback to a default directory
        root_dir = config.get("paths.stencil_directory", "./test_data")
        # Store it in session state for next time
        st.session_state.last_dir = root_dir
        
    # Scan button
    scan_col1, scan_col2 = st.columns([1, 4])
    with scan_col1:
        scan_btn = st.button("🔬 Analyze", use_container_width=True, key="health_scan_btn")
        
    # Handle scanning
    if scan_btn and not st.session_state.health_scan_running:
        if not os.path.exists(root_dir):
            st.error(f"Directory does not exist: {root_dir}")
        else:
            background_health_scan(root_dir)
    
    # Show scan progress if running
    if st.session_state.health_scan_running:
        st.progress(st.session_state.health_scan_progress / 100)
        st.caption("Analyzing stencil health...")
    
    # Display health analysis results if available
    if st.session_state.health_data:
        data = st.session_state.health_data
        
        # Show summary
        summary = data['summary']
        issues = data['issues']
        
        if summary['total_issues'] > 0:
            st.warning(f"Found {summary['total_issues']} potential issues in {summary['total_stencils']} stencils")
        else:
            st.success(f"No issues found in {summary['total_stencils']} stencils")
        
        # Quick overview in expandable section
        with st.expander("Health Analysis Summary"):
            # Metrics in two rows
            col1, col2, col3 = st.columns(3)
            col1.metric("Empty Stencils", summary['empty_stencils'])
            col2.metric("Stencils with Duplicate Shapes", summary['stencils_with_duplicates'])
            col3.metric("Corrupt Stencils", summary['corrupt_stencils'])
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Large Stencils", summary['large_stencils'])
            col2.metric("Version Conflicts", summary['version_conflicts'])
            col3.metric("Total Stencils Scanned", summary['total_stencils'])
            
            # Add health charts
            if len(issues) > 0:
                st.subheader("Health Charts")
                fig = generate_health_charts(data)
                st.pyplot(fig)
        
        # Display issues
        if issues:
            st.subheader("Issues Found")
            
            # Export options
            export_col1, export_col2 = st.columns([1, 1])
            with export_col1:
                csv_data = export_to_csv(data)
                st.download_button(
                    label="📋 Export to CSV",
                    data=csv_data,
                    file_name=f"stencil_health_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    key="export_csv"
                )
            with export_col2:
                excel_data = export_to_excel(data)
                st.download_button(
                    label="📊 Export to Excel",
                    data=excel_data,
                    file_name=f"stencil_health_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="export_excel"
                )
            
            # Filter options
            severity_options = ["All", "High", "Medium", "Low"]
            issue_types = ["All"] + list(set(issue['issue'].split(":")[0] for issue in issues))
            
            filter_col1, filter_col2 = st.columns(2)
            with filter_col1:
                selected_severity = st.selectbox("Filter by Severity", severity_options, key="sev_filter")
            with filter_col2:
                selected_type = st.selectbox("Filter by Issue Type", issue_types, key="type_filter")
            
            # Apply filters
            filtered_issues = issues
            if selected_severity != "All":
                filtered_issues = [issue for issue in filtered_issues if issue['severity'] == selected_severity]
            if selected_type != "All":
                filtered_issues = [issue for issue in filtered_issues if issue['issue'].startswith(selected_type)]
            
            # Display issues in a table
            issue_table = []
            for issue in filtered_issues:
                # Format severity with color
                if issue['severity'] == 'High':
                    severity_formatted = "🔴 High"
                elif issue['severity'] == 'Medium':
                    severity_formatted = "🟠 Medium"
                else:
                    severity_formatted = "🟡 Low"
                
                issue_table.append({
                    "Stencil": issue['name'],
                    "Issue": issue['issue'],
                    "Severity": severity_formatted,
                    "Path": issue['path']
                })
            
            # Convert to DataFrame for display
            df = pd.DataFrame(issue_table)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No issues found in your stencils! Everything looks healthy.")
    
    # Show shape preview if selected
    if st.session_state.preview_shape:
        with st.sidebar:
            st.subheader("Shape Preview")
            shape_data = st.session_state.preview_shape
            st.caption(f"From: {shape_data['stencil_name']}")
            
            # Get shape preview
            preview = get_shape_preview(shape_data['stencil_path'], shape_data['shape'])
            if preview:
                st.image(preview, use_column_width=True, caption=shape_data['shape'])
            else:
                st.error("Unable to generate preview")
            
            if st.button("Close Preview", key="close_preview"):
                st.session_state.preview_shape = None
                st.rerun()

# Only call main() once
if __name__ == "__main__":
    main()
else:
    main() 