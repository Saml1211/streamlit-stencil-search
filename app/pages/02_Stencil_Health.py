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

# Add the parent directory to path so we can import from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core import scan_directory, parse_visio_stencil, config, get_shape_preview
from app.core.db import StencilDatabase

# Set page config
st.set_page_config(
    page_title="Stencil Health Monitor",
    page_icon="🧪",
    layout="wide",
)

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
    """Run health scan in background"""
    try:
        st.session_state.health_scan_running = True
        st.session_state.health_scan_progress = 0
        
        # Run the health analysis
        health_data = analyze_stencil_health(root_dir)
        
        # Store results in session state
        st.session_state.health_data = health_data
    except Exception as e:
        st.error(f"Error during health scan: {str(e)}")
    finally:
        st.session_state.health_scan_running = False

def toggle_shape_preview(shape=None):
    """Toggle shape preview in session state"""
    st.session_state.preview_shape = shape

def main():
    # Inject JavaScript to track window width (for responsive design)
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
    
    st.title("Stencil Health Monitor")
    
    # Determine if mobile layout
    is_mobile = st.session_state.get('browser_width', 1200) < 768
    
    # Introduction - shortened for mobile
    if is_mobile:
        st.markdown("""
        This tool checks for:
        - Empty stencils
        - Duplicate shapes
        - Multiple versions
        - Large stencils
        - Corrupt files
        """)
    else:
        st.markdown("""
        This tool analyzes your Visio stencil files for potential issues:
        
        - **Empty stencils** that contain no shapes
        - **Duplicate shapes** within a single stencil
        - **Multiple versions** of the same stencil across directories
        - **Unusually large stencils** that exceed normal size limits
        - **Potentially corrupt files** that might cause Visio problems
        
        Use the export options to generate reports for further analysis.
        👀 **NEW**: Click on shape names to preview them!
        """)
    
    # Directory selection
    st.header("Select Directory")
    
    # Get default directory from config
    default_dir = config.get("paths.stencil_directory", "./test_data")
    if not os.path.exists(default_dir):
        default_dir = "./test_data" if os.path.exists("./test_data") else "Z:/ENGINEERING TEMPLATES/VISIO SHAPES 2025"
    
    root_dir = st.text_input(
        "Stencil Directory", 
        value=default_dir,
        help="Enter the directory containing Visio stencil files to analyze"
    )
    
    # Use full width button on mobile
    if is_mobile:
        scan_btn = st.button("🔍 Analyze Health", use_container_width=True)
    else:
        col1, col2 = st.columns([1, 3])
        with col1:
            scan_btn = st.button("🔍 Analyze Health", use_container_width=True)
    
    # Run health scan when button clicked
    if scan_btn and not st.session_state.health_scan_running:
        if not os.path.exists(root_dir):
            st.error(f"Directory does not exist: {root_dir}")
        else:
            background_health_scan(root_dir)
            st.rerun()
    
    # Show progress during scan
    if st.session_state.health_scan_running:
        st.progress(st.session_state.health_scan_progress / 100.0, "Analyzing stencil health...")
    
    # Display results if available
    if st.session_state.health_data:
        data = st.session_state.health_data
        summary = data['summary']
        issues = data['issues']
        
        # Summary section
        st.header("Health Summary")
        
        # Adjust layout for mobile
        if is_mobile:
            st.metric("Stencils", summary['total_stencils'])
            st.metric("Issues", summary['total_issues'])
            st.metric("Empty", summary['empty_stencils'])
            st.metric("Corrupt", summary.get('corrupt_stencils', 0))
            st.metric("Conflicts", summary['version_conflicts'])
        else:
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Stencils Analyzed", summary['total_stencils'])
            col2.metric("Total Issues", summary['total_issues'])
            col3.metric("Empty Stencils", summary['empty_stencils'])
            col4.metric("Corrupt Files", summary.get('corrupt_stencils', 0))
            col5.metric("Version Conflicts", summary['version_conflicts'])
        
        st.caption(f"Scan completed: {summary['scan_time']}")
        
        # Show health charts
        if not is_mobile:  # Only show charts on desktop
            st.subheader("Health Visualization")
            chart_image = generate_health_charts(data)
            st.image(chart_image, use_column_width=True)
        
        # Export buttons
        st.header("Export Options")
        
        # Stack vertically on mobile, side by side on desktop
        if is_mobile:
            csv_data = export_to_csv(data)
            st.download_button(
                label="📄 Export Issues (CSV)",
                data=csv_data,
                file_name=f"stencil_issues_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
            excel_data = export_to_excel(data)
            st.download_button(
                label="📊 Export Full Report (Excel)",
                data=excel_data,
                file_name=f"stencil_health_report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        else:
            col1, col2 = st.columns(2)
            
            with col1:
                csv_data = export_to_csv(data)
                st.download_button(
                    label="📄 Export Issues to CSV",
                    data=csv_data,
                    file_name=f"stencil_issues_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            
            with col2:
                excel_data = export_to_excel(data)
                st.download_button(
                    label="📊 Export Full Report (Excel)",
                    data=excel_data,
                    file_name=f"stencil_health_report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        
        # Display shape preview if active
        if st.session_state.preview_shape:
            preview_col1, preview_col2 = st.columns([1, 3])
            with preview_col1:
                # Generate and display shape preview
                shape_preview = get_shape_preview(st.session_state.preview_shape)
                st.image(shape_preview, width=150)
                st.caption(f"Preview of '{st.session_state.preview_shape}'")
                
                # Close button
                if st.button("Close Preview"):
                    st.session_state.preview_shape = None
                    st.rerun()
        
        # Issues table
        st.header("Detected Issues")
        if issues:
            # Create a dataframe for better display
            issues_df = pd.DataFrame(issues)
            
            # Add severity filter
            severity_filter = st.multiselect(
                "Filter by Severity:",
                options=["High", "Medium", "Low"],
                default=["High", "Medium", "Low"]
            )
            
            # Add issue type filter
            issue_types = issues_df['issue'].apply(lambda x: x.split(':')[0] if ':' in x else x.split('(')[0].strip())
            unique_issue_types = sorted(issue_types.unique())
            
            type_filter = st.multiselect(
                "Filter by Issue Type:",
                options=unique_issue_types,
                default=unique_issue_types
            )
            
            # Filter the dataframe
            filtered_df = issues_df[
                (issues_df['severity'].isin(severity_filter)) & 
                (issues_df['issue'].apply(lambda x: any(t in x for t in type_filter)))
            ]
            
            if not filtered_df.empty:
                # Use different display for mobile vs desktop
                if is_mobile:
                    # Use a more compact display for mobile
                    for i, row in filtered_df.iterrows():
                        with st.container(border=True):
                            st.markdown(f"**{row['name']}**")
                            st.markdown(f"**Issue:** {row['issue']}")
                            st.markdown(f"**Severity:** {row['severity']}")
                            st.markdown(f"**Path:** `{row['path']}`")
                            
                            # Add preview button if this issue has a shape
                            if 'shape' in row and row['shape']:
                                if st.button(f"👁️ Preview Shape: {row['shape'][:20]}...", key=f"preview_{i}"):
                                    toggle_shape_preview(row['shape'])
                                    st.rerun()
                            elif 'Duplicate shape' in row['issue']:
                                # Extract shape name from issue text
                                shape_match = re.search(r'"([^"]+)"', row['issue'])
                                if shape_match:
                                    shape_name = shape_match.group(1)
                                    if st.button(f"👁️ Preview Shape: {shape_name[:20]}...", key=f"preview_{i}"):
                                        toggle_shape_preview(shape_name)
                                        st.rerun()
                            elif 'shapes' in row and row['shapes'] and len(row['shapes']) > 0:
                                # For stencils with shapes, allow preview of the first 5
                                st.markdown("**Preview shapes:**")
                                for j, shape in enumerate(row['shapes'][:5]):
                                    if st.button(f"👁️ {shape[:20]}...", key=f"preview_{i}_{j}"):
                                        toggle_shape_preview(shape)
                                        st.rerun()
                                if len(row['shapes']) > 5:
                                    st.caption(f"...and {len(row['shapes'])-5} more")
                else:
                    # Use dataframe for desktop with custom columns
                    df_view = filtered_df.copy()
                    
                    # Add a preview column
                    def make_clickable(row):
                        # For duplicate shape issues
                        if 'Duplicate shape' in row['issue']:
                            shape_match = re.search(r'"([^"]+)"', row['issue'])
                            if shape_match:
                                shape_name = shape_match.group(1)
                                return f"[👁️ Preview](javascript:void)"
                        # For rows with explicit shape field
                        elif 'shape' in row and row['shape']:
                            return f"[👁️ Preview](javascript:void)"
                        # For rows with shapes list
                        elif 'shapes' in row and row['shapes'] and len(row['shapes']) > 0:
                            return f"[👁️ Preview First](javascript:void)"
                        return ""
                    
                    # Add preview column if it doesn't exist
                    df_view['preview'] = df_view.apply(make_clickable, axis=1)
                    
                    # Show dataframe with clickable preview links
                    clicked = st.dataframe(
                        df_view,
                        column_config={
                            "path": st.column_config.TextColumn("File Path"),
                            "name": st.column_config.TextColumn("Stencil Name"),
                            "issue": st.column_config.TextColumn("Issue Description"),
                            "severity": st.column_config.TextColumn("Severity"),
                            "preview": st.column_config.LinkColumn("Preview")
                        },
                        hide_index=True,
                        column_order=["name", "issue", "severity", "preview", "path"]
                    )
                    
                    # Handle click on dataframe
                    if clicked:
                        selected_row = clicked["selected_rows"][0]
                        
                        # Determine which shape to preview
                        if 'Duplicate shape' in selected_row["issue"]:
                            shape_match = re.search(r'"([^"]+)"', selected_row["issue"])
                            if shape_match:
                                toggle_shape_preview(shape_match.group(1))
                                st.rerun()
                        elif 'shape' in selected_row and selected_row["shape"]:
                            toggle_shape_preview(selected_row["shape"])
                            st.rerun()
                        elif 'shapes' in selected_row and selected_row["shapes"] and len(selected_row["shapes"]) > 0:
                            toggle_shape_preview(selected_row["shapes"][0])
                            st.rerun()
            else:
                st.info("No issues match the selected filters.")
        else:
            st.success("No issues detected! Your stencils appear to be healthy.")
    else:
        st.info("Click 'Analyze Health' to scan your stencil files for potential issues.")

if __name__ == "__main__":
    main() 