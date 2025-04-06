import streamlit as st
import os
import sys
import time
from typing import List, Dict, Any, Optional, Tuple

# Add the parent directory to path so we can import from core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import config, visio
from app.core.components import render_shared_sidebar

# Session state is now initialized in app.py
# No need to initialize session state variables here

# Sidebar is now rendered in app.py

def refresh_visio_connection():
    """Refresh the Visio connection and update session state"""
    # Get server name if using remote connection
    server_name = None
    if st.session_state.get('visio_connection_type', 'local') == 'remote':
        server_name = st.session_state.get('visio_server_name', '')
        if not server_name:
            st.warning("Remote connection selected but no server name provided. Using local connection.")
            server_name = None

    connected = visio.connect(server_name)
    st.session_state.visio_connected = connected

    if connected:
        st.session_state.visio_documents = visio.get_open_documents()

        # Get default document and page if available
        doc_index, page_index, found_valid = visio.get_default_document_page()
        if found_valid:
            st.session_state.selected_doc_index = doc_index
            st.session_state.selected_page_index = page_index

    return connected

def create_new_document(doc_name: str) -> bool:
    """Create a new Visio document"""
    if not st.session_state.visio_connected:
        return False

    try:
        success = visio.create_new_document(doc_name)
        if success:
            # Refresh document list
            st.session_state.visio_documents = visio.get_open_documents()
        return success
    except Exception as e:
        st.error(f"Error creating document: {str(e)}")
        return False

def create_new_page(doc_index: int, page_name: str) -> bool:
    """Create a new page in the selected document"""
    if not st.session_state.visio_connected:
        return False

    try:
        success = visio.create_new_page(doc_index, page_name)
        return success
    except Exception as e:
        st.error(f"Error creating page: {str(e)}")
        return False

def rename_page(doc_index: int, page_index: int, new_name: str) -> bool:
    """Rename a page in the selected document"""
    if not st.session_state.visio_connected:
        return False

    try:
        success = visio.rename_page(doc_index, page_index, new_name)
        return success
    except Exception as e:
        st.error(f"Error renaming page: {str(e)}")
        return False

def get_shapes_in_page(doc_index: int, page_index: int) -> list:
    """Get shapes in the selected page"""
    if not st.session_state.visio_connected:
        return []

    try:
        shapes = visio.get_shapes_in_page(doc_index, page_index)
        return shapes
    except Exception as e:
        st.error(f"Error getting shapes: {str(e)}")
        return []

def select_shape(doc_index: int, page_index: int, shape_id: int) -> bool:
    """Select a shape in Visio"""
    if not st.session_state.visio_connected:
        return False

    try:
        success = visio.select_shape(doc_index, page_index, shape_id)
        if success:
            st.session_state.selected_shape_id = shape_id
        return success
    except Exception as e:
        st.error(f"Error selecting shape: {str(e)}")
        return False

def delete_shape(doc_index: int, page_index: int, shape_id: int) -> bool:
    """Delete a shape from the page"""
    if not st.session_state.visio_connected:
        return False

    try:
        success = visio.delete_shape(doc_index, page_index, shape_id)
        if success and st.session_state.selected_shape_id == shape_id:
            st.session_state.selected_shape_id = None
        return success
    except Exception as e:
        st.error(f"Error deleting shape: {str(e)}")
        return False

def update_shape_text(doc_index: int, page_index: int, shape_id: int, new_text: str) -> bool:
    """Update the text of a shape"""
    if not st.session_state.visio_connected:
        return False

    try:
        success = visio.update_shape_text(doc_index, page_index, shape_id, new_text)
        return success
    except Exception as e:
        st.error(f"Error updating shape text: {str(e)}")
        return False

def move_shape(doc_index: int, page_index: int, shape_id: int, x: float, y: float) -> bool:
    """Move a shape to a new position"""
    if not st.session_state.visio_connected:
        return False

    try:
        success = visio.move_shape(doc_index, page_index, shape_id, x, y)
        return success
    except Exception as e:
        st.error(f"Error moving shape: {str(e)}")
        return False

def resize_shape(doc_index: int, page_index: int, shape_id: int, width: float, height: float) -> bool:
    """Resize a shape"""
    if not st.session_state.visio_connected:
        return False

    try:
        success = visio.resize_shape(doc_index, page_index, shape_id, width, height)
        return success
    except Exception as e:
        st.error(f"Error resizing shape: {str(e)}")
        return False

def create_basic_shape(doc_index: int, page_index: int, shape_type: str, x: float, y: float, width: float, height: float) -> Optional[int]:
    """Create a basic shape on the page"""
    if not st.session_state.visio_connected:
        return None

    try:
        shape_id = visio.create_basic_shape(doc_index, page_index, shape_type, x, y, width, height)
        return shape_id
    except Exception as e:
        st.error(f"Error creating shape: {str(e)}")
        return None

def align_shapes(doc_index: int, page_index: int, shape_ids: List[int], alignment: str) -> bool:
    """Align shapes on the page"""
    if not st.session_state.visio_connected:
        return False

    try:
        success = visio.align_shapes(doc_index, page_index, shape_ids, alignment)
        return success
    except Exception as e:
        st.error(f"Error aligning shapes: {str(e)}")
        return False

def change_shape_order(doc_index: int, page_index: int, shape_id: int, order_action: str) -> bool:
    """Change the z-order of a shape"""
    if not st.session_state.visio_connected:
        return False

    try:
        success = visio.change_shape_order(doc_index, page_index, shape_id, order_action)
        return success
    except Exception as e:
        st.error(f"Error changing shape order: {str(e)}")
        return False

def main(selected_directory=None):
    # Page title and description
    st.title("Visio Control")

    # Page description
    st.markdown("""
    This page provides direct control over Microsoft Visio, allowing you to manage documents,
    pages, and perform basic operations without switching applications.
    """)

    # About section using expander component
    with st.expander("About Visio Control"):
        st.markdown("""
        ### Visio Control Panel

        This tool allows you to:

        - Create new Visio documents
        - Manage pages within documents
        - Create basic shapes (rectangle, ellipse, line, triangle)
        - View and edit shapes on pages
        - Modify shape properties (text, size, position)
        - Align multiple shapes (left, center, right, top, middle, bottom)
        - Change shape stacking order (z-order)
        - Connect to local or remote Visio instances
        - View document properties
        - Perform basic Visio operations

        Use this interface to control Visio directly from Streamlit without switching applications.
        """)

    # Check if we're on mobile based on browser width
    is_mobile = st.session_state.get('browser_width', 1200) < 768

    # Visio connection status
    status_col1, status_col2 = st.columns([3, 1])

    with status_col1:
        if st.session_state.get('visio_connected', False):
            if st.session_state.get('visio_documents', []):
                st.success(f"Connected to Visio ({len(st.session_state.visio_documents)} document(s) open)")
            else:
                st.warning("Connected to Visio, but no documents open")
        else:
            st.error("Not connected to Visio")

    with status_col2:
        refresh_btn = st.button("🔄 Refresh", key="refresh_visio_control", use_container_width=True)
        if refresh_btn:
            with st.spinner("Connecting to Visio..."):
                refresh_visio_connection()
                st.rerun()

    # Main content area with tabs
    if not st.session_state.get('visio_connected', False):
        st.info("Please connect to Visio using the refresh button above.")
    else:
        # Create tabs for different control sections
        tabs = st.tabs(["Documents", "Pages", "Shapes", "Properties"])

        # DOCUMENTS TAB
        with tabs[0]:
            st.subheader("Document Management")

            # Create new document section
            with st.container(border=True):
                st.write("#### Create New Document")

                new_doc_col1, new_doc_col2 = st.columns([3, 1])

                with new_doc_col1:
                    new_doc_name = st.text_input(
                        "Document Name",
                        value=st.session_state.new_doc_name,
                        key="new_doc_name_input"
                    )
                    st.session_state.new_doc_name = new_doc_name

                with new_doc_col2:
                    st.write("")  # Spacing
                    create_doc_btn = st.button("Create", key="create_doc_btn", use_container_width=True)

                    if create_doc_btn:
                        with st.spinner(f"Creating document '{new_doc_name}'..."):
                            success = create_new_document(new_doc_name)
                            if success:
                                st.success(f"Document '{new_doc_name}' created successfully")
                                st.rerun()
                            else:
                                st.error("Failed to create document")

            # List open documents
            with st.container(border=True):
                st.write("#### Open Documents")

                if not st.session_state.get('visio_documents', []):
                    st.info("No documents currently open in Visio")
                else:
                    # Create a table of open documents
                    for idx, doc in enumerate(st.session_state.visio_documents):
                        doc_col1, doc_col2, doc_col3 = st.columns([3, 1, 1])

                        with doc_col1:
                            st.write(f"**{doc['name']}**")
                            st.caption(f"Path: {doc['path']}")

                        with doc_col2:
                            is_selected = st.session_state.selected_doc_index == doc['index']
                            if is_selected:
                                st.success("Selected")
                            else:
                                if st.button("Select", key=f"select_doc_{idx}"):
                                    st.session_state.selected_doc_index = doc['index']
                                    st.rerun()

                        with doc_col3:
                            if st.button("Close", key=f"close_doc_{idx}"):
                                with st.spinner(f"Closing document '{doc['name']}'..."):
                                    success = visio.close_document(doc['index'])
                                    if success:
                                        st.success(f"Document '{doc['name']}' closed")
                                        # Refresh document list
                                        st.session_state.visio_documents = visio.get_open_documents()
                                        st.rerun()
                                    else:
                                        st.error("Failed to close document")

        # PAGES TAB
        with tabs[1]:
            st.subheader("Page Management")

            # Check if we have a selected document
            if not st.session_state.get('visio_documents', []):
                st.info("No documents open. Please open or create a document first.")
            else:
                # Get the selected document
                selected_doc_idx = st.session_state.selected_doc_index
                selected_doc = None

                for doc in st.session_state.visio_documents:
                    if doc['index'] == selected_doc_idx:
                        selected_doc = doc
                        break

                if not selected_doc:
                    st.warning("No document selected. Please select a document from the Documents tab.")
                else:
                    st.write(f"Working with document: **{selected_doc['name']}**")

                    # Create new page section
                    with st.container(border=True):
                        st.write("#### Create New Page")

                        new_page_col1, new_page_col2 = st.columns([3, 1])

                        with new_page_col1:
                            new_page_name = st.text_input(
                                "Page Name",
                                value=st.session_state.new_page_name,
                                key="new_page_name_input"
                            )
                            st.session_state.new_page_name = new_page_name

                        with new_page_col2:
                            st.write("")  # Spacing
                            create_page_btn = st.button("Create", key="create_page_btn", use_container_width=True)

                            if create_page_btn:
                                with st.spinner(f"Creating page '{new_page_name}'..."):
                                    success = create_new_page(selected_doc_idx, new_page_name)
                                    if success:
                                        st.success(f"Page '{new_page_name}' created successfully")
                                        st.rerun()
                                    else:
                                        st.error("Failed to create page")

                    # List pages in document
                    with st.container(border=True):
                        st.write("#### Pages in Document")

                        # Get pages in the selected document
                        pages = visio.get_pages_in_document(selected_doc_idx)

                        if not pages:
                            st.info("No pages found in this document")
                        else:
                            # Create a table of pages
                            for idx, page in enumerate(pages):
                                page_col1, page_col2, page_col3 = st.columns([3, 1, 1])

                                with page_col1:
                                    page_label = page['name']
                                    if page['is_foreground']:
                                        page_label += " (Foreground)"
                                    if page['is_schematic']:
                                        page_label += " (Schematic)"

                                    st.write(f"**{page_label}**")

                                with page_col2:
                                    is_selected = st.session_state.selected_page_index == page['index']
                                    if is_selected:
                                        st.success("Selected")
                                    else:
                                        if st.button("Select", key=f"select_page_{idx}"):
                                            st.session_state.selected_page_index = page['index']
                                            st.rerun()

                                with page_col3:
                                    if st.button("Rename", key=f"rename_page_{idx}"):
                                        # Show rename form
                                        with st.form(key=f"rename_page_form_{idx}"):
                                            st.subheader(f"Rename Page: {page['name']}")
                                            new_name = st.text_input("New Name", value=page['name'])

                                            rename_submitted = st.form_submit_button("Rename")
                                            if rename_submitted:
                                                success = rename_page(selected_doc_idx, page['index'], new_name)
                                                if success:
                                                    st.success(f"Page renamed to '{new_name}'")
                                                    st.rerun()
                                                else:
                                                    st.error("Failed to rename page")

        # SHAPES TAB
        with tabs[2]:
            st.subheader("Shape Management")

            # Check if we have a selected document and page
            if not st.session_state.get('visio_documents', []):
                st.info("No documents open. Please open or create a document first.")
            else:
                # Get the selected document and page
                selected_doc_idx = st.session_state.selected_doc_index
                selected_page_idx = st.session_state.selected_page_index
                selected_doc = None

                for doc in st.session_state.visio_documents:
                    if doc['index'] == selected_doc_idx:
                        selected_doc = doc
                        break

                if not selected_doc:
                    st.warning("No document selected. Please select a document from the Documents tab.")
                else:
                    st.write(f"Working with document: **{selected_doc['name']}**")

                    # Get pages in the selected document
                    pages = visio.get_pages_in_document(selected_doc_idx)
                    selected_page = None

                    for page in pages:
                        if page['index'] == selected_page_idx:
                            selected_page = page
                            break

                    if not selected_page:
                        st.warning("No page selected. Please select a page from the Pages tab.")
                    else:
                        st.write(f"Current page: **{selected_page['name']}**")

                        # Get shapes in the current page
                        shapes = get_shapes_in_page(selected_doc_idx, selected_page_idx)

                        # Shape creation section
                        with st.container(border=True):
                            st.write("#### Create New Shape")

                            # Shape type selector
                            shape_type_col, shape_create_col = st.columns([3, 1])

                            with shape_type_col:
                                shape_type = st.selectbox(
                                    "Shape Type",
                                    options=["Rectangle", "Ellipse", "Line", "Triangle"],
                                    index=0,
                                    key="shape_type_selector"
                                )
                                st.session_state.new_shape_type = shape_type.lower()

                            # Size and position inputs in a 2x2 grid
                            size_pos_col1, size_pos_col2 = st.columns(2)

                            with size_pos_col1:
                                new_width = st.number_input(
                                    "Width",
                                    value=float(st.session_state.new_shape_width),
                                    min_value=0.1,
                                    step=0.1,
                                    format="%.2f",
                                    key="new_shape_width_input"
                                )
                                st.session_state.new_shape_width = new_width

                                new_x = st.number_input(
                                    "X Position",
                                    value=float(st.session_state.new_shape_x),
                                    step=0.1,
                                    format="%.2f",
                                    key="new_shape_x_input"
                                )
                                st.session_state.new_shape_x = new_x

                            with size_pos_col2:
                                new_height = st.number_input(
                                    "Height",
                                    value=float(st.session_state.new_shape_height),
                                    min_value=0.1,
                                    step=0.1,
                                    format="%.2f",
                                    key="new_shape_height_input"
                                )
                                st.session_state.new_shape_height = new_height

                                new_y = st.number_input(
                                    "Y Position",
                                    value=float(st.session_state.new_shape_y),
                                    step=0.1,
                                    format="%.2f",
                                    key="new_shape_y_input"
                                )
                                st.session_state.new_shape_y = new_y

                            with shape_create_col:
                                st.write("")
                                st.write("")
                                if st.button("Create", key="create_shape_btn", use_container_width=True):
                                    with st.spinner(f"Creating {shape_type.lower()} shape..."):
                                        shape_id = create_basic_shape(
                                            selected_doc_idx,
                                            selected_page_idx,
                                            st.session_state.new_shape_type,
                                            st.session_state.new_shape_x,
                                            st.session_state.new_shape_y,
                                            st.session_state.new_shape_width,
                                            st.session_state.new_shape_height
                                        )
                                        if shape_id:
                                            st.success(f"Created {shape_type.lower()} shape")
                                            st.rerun()
                                        else:
                                            st.error(f"Failed to create {shape_type.lower()} shape")

                        # Shape list section
                        with st.container(border=True):
                            st.write("#### Shapes on Page")

                            if not shapes:
                                st.info("No shapes found on this page.")
                            else:
                                st.write(f"Found {len(shapes)} shape(s) on this page.")

                                # Create a table of shapes
                                for idx, shape in enumerate(shapes):
                                    shape_col1, shape_col2, shape_col3, shape_col4 = st.columns([3, 1, 1, 1])

                                    with shape_col1:
                                        shape_label = shape['name'] if shape['name'] else "(Unnamed Shape)"
                                        if shape['text']:
                                            shape_label += f" - '{shape['text']}'"

                                        st.write(f"**{shape_label}**")
                                        st.caption(f"Type: {shape['type']}, Master: {shape['master']}")

                                    with shape_col2:
                                        is_selected = st.session_state.selected_shape_id == shape['id']
                                        if is_selected:
                                            st.success("Selected")
                                        else:
                                            if st.button("Select", key=f"select_shape_{idx}"):
                                                with st.spinner(f"Selecting shape '{shape_label}'..."):
                                                    success = select_shape(selected_doc_idx, selected_page_idx, shape['id'])
                                                    if success:
                                                        # Store shape properties for editing
                                                        st.session_state.shape_edit_text = shape['text']
                                                        st.session_state.shape_edit_width = shape['width']
                                                        st.session_state.shape_edit_height = shape['height']
                                                        st.session_state.shape_edit_x = shape['position_x']
                                                        st.session_state.shape_edit_y = shape['position_y']
                                                        st.rerun()

                                    with shape_col3:
                                        # Add to alignment selection
                                        is_in_alignment = shape['id'] in st.session_state.selected_shapes_for_alignment
                                        if is_in_alignment:
                                            if st.button("✓", key=f"remove_align_{idx}"):
                                                st.session_state.selected_shapes_for_alignment.remove(shape['id'])
                                                st.rerun()
                                        else:
                                            if st.button("+", key=f"add_align_{idx}", help="Add to alignment selection"):
                                                st.session_state.selected_shapes_for_alignment.append(shape['id'])
                                                st.rerun()

                                    with shape_col4:
                                        if st.button("Delete", key=f"delete_shape_{idx}"):
                                            with st.spinner(f"Deleting shape '{shape_label}'..."):
                                                success = delete_shape(selected_doc_idx, selected_page_idx, shape['id'])
                                                if success:
                                                    # Also remove from alignment selection if present
                                                    if shape['id'] in st.session_state.selected_shapes_for_alignment:
                                                        st.session_state.selected_shapes_for_alignment.remove(shape['id'])
                                                    st.success(f"Shape '{shape_label}' deleted")
                                                    st.rerun()

                                # Alignment tools - only show if at least 2 shapes are selected for alignment
                                if len(st.session_state.selected_shapes_for_alignment) >= 2:
                                    st.write("**Alignment Tools**")
                                    st.caption(f"{len(st.session_state.selected_shapes_for_alignment)} shapes selected for alignment")

                                    align_col1, align_col2, align_col3 = st.columns(3)

                                    with align_col1:
                                        if st.button("Align Left", key="align_left_btn"):
                                            with st.spinner("Aligning shapes to the left..."):
                                                success = align_shapes(
                                                    selected_doc_idx,
                                                    selected_page_idx,
                                                    st.session_state.selected_shapes_for_alignment,
                                                    "left"
                                                )
                                                if success:
                                                    st.success("Shapes aligned to the left")
                                                    st.rerun()

                                        if st.button("Align Top", key="align_top_btn"):
                                            with st.spinner("Aligning shapes to the top..."):
                                                success = align_shapes(
                                                    selected_doc_idx,
                                                    selected_page_idx,
                                                    st.session_state.selected_shapes_for_alignment,
                                                    "top"
                                                )
                                                if success:
                                                    st.success("Shapes aligned to the top")
                                                    st.rerun()

                                    with align_col2:
                                        if st.button("Align Center", key="align_center_btn"):
                                            with st.spinner("Aligning shapes to the center..."):
                                                success = align_shapes(
                                                    selected_doc_idx,
                                                    selected_page_idx,
                                                    st.session_state.selected_shapes_for_alignment,
                                                    "center"
                                                )
                                                if success:
                                                    st.success("Shapes aligned to the center")
                                                    st.rerun()

                                        if st.button("Align Middle", key="align_middle_btn"):
                                            with st.spinner("Aligning shapes to the middle..."):
                                                success = align_shapes(
                                                    selected_doc_idx,
                                                    selected_page_idx,
                                                    st.session_state.selected_shapes_for_alignment,
                                                    "middle"
                                                )
                                                if success:
                                                    st.success("Shapes aligned to the middle")
                                                    st.rerun()

                                    with align_col3:
                                        if st.button("Align Right", key="align_right_btn"):
                                            with st.spinner("Aligning shapes to the right..."):
                                                success = align_shapes(
                                                    selected_doc_idx,
                                                    selected_page_idx,
                                                    st.session_state.selected_shapes_for_alignment,
                                                    "right"
                                                )
                                                if success:
                                                    st.success("Shapes aligned to the right")
                                                    st.rerun()

                                        if st.button("Align Bottom", key="align_bottom_btn"):
                                            with st.spinner("Aligning shapes to the bottom..."):
                                                success = align_shapes(
                                                    selected_doc_idx,
                                                    selected_page_idx,
                                                    st.session_state.selected_shapes_for_alignment,
                                                    "bottom"
                                                )
                                                if success:
                                                    st.success("Shapes aligned to the bottom")
                                                    st.rerun()

                                    # Clear selection button
                                    if st.button("Clear Selection", key="clear_alignment_selection_btn"):
                                        st.session_state.selected_shapes_for_alignment = []
                                        st.rerun()

                        # Shape editing section - only show if a shape is selected
                        if st.session_state.selected_shape_id is not None:
                            with st.container(border=True):
                                st.write("#### Edit Selected Shape")

                                # Find the selected shape
                                selected_shape = None
                                for shape in shapes:
                                    if shape['id'] == st.session_state.selected_shape_id:
                                        selected_shape = shape
                                        break

                                if not selected_shape:
                                    st.warning("Selected shape not found. It may have been deleted.")
                                    st.session_state.selected_shape_id = None
                                else:
                                    # Shape properties editor
                                    shape_name = selected_shape['name'] if selected_shape['name'] else "(Unnamed Shape)"
                                    st.write(f"Editing shape: **{shape_name}**")

                                    # Text editor
                                    text_col1, text_col2 = st.columns([3, 1])

                                    with text_col1:
                                        new_text = st.text_input(
                                            "Shape Text",
                                            value=st.session_state.shape_edit_text,
                                            key="shape_text_input"
                                        )
                                        st.session_state.shape_edit_text = new_text

                                    with text_col2:
                                        if st.button("Update Text", key="update_shape_text_btn"):
                                            with st.spinner("Updating shape text..."):
                                                success = update_shape_text(
                                                    selected_doc_idx,
                                                    selected_page_idx,
                                                    selected_shape['id'],
                                                    new_text
                                                )
                                                if success:
                                                    st.success("Shape text updated")
                                                    st.rerun()

                                    # Size editor
                                    st.write("**Size**")
                                    size_col1, size_col2, size_col3 = st.columns([2, 2, 1])

                                    with size_col1:
                                        new_width = st.number_input(
                                            "Width",
                                            value=float(st.session_state.shape_edit_width),
                                            min_value=0.1,
                                            step=0.1,
                                            format="%.2f",
                                            key="shape_width_input"
                                        )
                                        st.session_state.shape_edit_width = new_width

                                    with size_col2:
                                        new_height = st.number_input(
                                            "Height",
                                            value=float(st.session_state.shape_edit_height),
                                            min_value=0.1,
                                            step=0.1,
                                            format="%.2f",
                                            key="shape_height_input"
                                        )
                                        st.session_state.shape_edit_height = new_height

                                    with size_col3:
                                        if st.button("Resize", key="resize_shape_btn"):
                                            with st.spinner("Resizing shape..."):
                                                success = resize_shape(
                                                    selected_doc_idx,
                                                    selected_page_idx,
                                                    selected_shape['id'],
                                                    new_width,
                                                    new_height
                                                )
                                                if success:
                                                    st.success("Shape resized")
                                                    st.rerun()

                                    # Position editor
                                    st.write("**Position**")
                                    pos_col1, pos_col2, pos_col3 = st.columns([2, 2, 1])

                                    with pos_col1:
                                        new_x = st.number_input(
                                            "X Position",
                                            value=float(st.session_state.shape_edit_x),
                                            step=0.1,
                                            format="%.2f",
                                            key="shape_x_input"
                                        )
                                        st.session_state.shape_edit_x = new_x

                                    with pos_col2:
                                        new_y = st.number_input(
                                            "Y Position",
                                            value=float(st.session_state.shape_edit_y),
                                            step=0.1,
                                            format="%.2f",
                                            key="shape_y_input"
                                        )
                                        st.session_state.shape_edit_y = new_y

                                    with pos_col3:
                                        if st.button("Move", key="move_shape_btn"):
                                            with st.spinner("Moving shape..."):
                                                success = move_shape(
                                                    selected_doc_idx,
                                                    selected_page_idx,
                                                    selected_shape['id'],
                                                    new_x,
                                                    new_y
                                                )
                                                if success:
                                                    st.success("Shape moved")
                                                    st.rerun()

                                    # Z-Order controls
                                    st.write("**Z-Order**")
                                    st.caption("Change the stacking order of the shape")

                                    order_col1, order_col2, order_col3, order_col4 = st.columns(4)

                                    with order_col1:
                                        if st.button("Bring to Front", key="bring_to_front_btn"):
                                            with st.spinner("Bringing shape to front..."):
                                                success = change_shape_order(
                                                    selected_doc_idx,
                                                    selected_page_idx,
                                                    selected_shape['id'],
                                                    "bring_to_front"
                                                )
                                                if success:
                                                    st.success("Shape brought to front")
                                                    st.rerun()

                                    with order_col2:
                                        if st.button("Send to Back", key="send_to_back_btn"):
                                            with st.spinner("Sending shape to back..."):
                                                success = change_shape_order(
                                                    selected_doc_idx,
                                                    selected_page_idx,
                                                    selected_shape['id'],
                                                    "send_to_back"
                                                )
                                                if success:
                                                    st.success("Shape sent to back")
                                                    st.rerun()

                                    with order_col3:
                                        if st.button("Bring Forward", key="bring_forward_btn"):
                                            with st.spinner("Bringing shape forward..."):
                                                success = change_shape_order(
                                                    selected_doc_idx,
                                                    selected_page_idx,
                                                    selected_shape['id'],
                                                    "bring_forward"
                                                )
                                                if success:
                                                    st.success("Shape brought forward")
                                                    st.rerun()

                                    with order_col4:
                                        if st.button("Send Backward", key="send_backward_btn"):
                                            with st.spinner("Sending shape backward..."):
                                                success = change_shape_order(
                                                    selected_doc_idx,
                                                    selected_page_idx,
                                                    selected_shape['id'],
                                                    "send_backward"
                                                )
                                                if success:
                                                    st.success("Shape sent backward")
                                                    st.rerun()

        # PROPERTIES TAB
        with tabs[3]:
            st.subheader("Document Properties")

            # Check if we have a selected document
            if not st.session_state.get('visio_documents', []):
                st.info("No documents open. Please open or create a document first.")
            else:
                # Get the selected document
                selected_doc_idx = st.session_state.selected_doc_index
                selected_doc = None

                for doc in st.session_state.visio_documents:
                    if doc['index'] == selected_doc_idx:
                        selected_doc = doc
                        break

                if not selected_doc:
                    st.warning("No document selected. Please select a document from the Documents tab.")
                else:
                    # Display document properties
                    with st.container(border=True):
                        st.write("#### Basic Properties")

                        properties_col1, properties_col2 = st.columns(2)

                        with properties_col1:
                            st.write("**Document Name:**")
                            st.write("**Path:**")
                            st.write("**Full Name:**")

                        with properties_col2:
                            st.write(selected_doc['name'])
                            st.write(selected_doc['path'])
                            st.write(selected_doc['full_name'])

                    # Document actions
                    with st.container(border=True):
                        st.write("#### Document Actions")

                        action_col1, action_col2 = st.columns(2)

                        with action_col1:
                            if st.button("Save Document", key="save_doc_btn", use_container_width=True):
                                with st.spinner("Saving document..."):
                                    success = visio.save_document(selected_doc_idx)
                                    if success:
                                        st.success("Document saved successfully")
                                    else:
                                        st.error("Failed to save document")

                        with action_col2:
                            if st.button("Save As...", key="save_as_doc_btn", use_container_width=True):
                                # Show save as form
                                with st.form(key="save_as_form"):
                                    st.subheader("Save Document As")
                                    save_path = st.text_input("File Path", value=selected_doc['path'])

                                    save_submitted = st.form_submit_button("Save")
                                    if save_submitted:
                                        success = visio.save_document_as(selected_doc_idx, save_path)
                                        if success:
                                            st.success(f"Document saved to '{save_path}'")
                                            # Refresh document list
                                            st.session_state.visio_documents = visio.get_open_documents()
                                            st.rerun()
                                        else:
                                            st.error("Failed to save document")

# Call main() only once
if __name__ == "__main__":
    main()
else:
    # main() is now called from app.py with the selected_directory parameter
    pass
