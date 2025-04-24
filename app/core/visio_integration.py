import os
import sys
import logging
import re
from typing import List, Dict, Tuple, Optional, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("visio_integration")

# Flag to track if win32com is available
win32com_available = False

try:
    import win32com.client
    import pythoncom  # Import pythoncom for COM initialization
    from win32com.client import constants as const
    win32com_available = True
except ImportError:
    logger.warning("win32com not available. Visio integration features will be disabled.")

class VisioIntegration:
    """Class for integrating with Microsoft Visio via COM"""

    def __init__(self):
        """Initialize Visio integration"""
        self.visio_app = None
        self._connect_attempts = 0
        self.available = win32com_available
        self.server_name = None  # Remote server name, None for local

    def _normalize_path(self, path: str) -> str:
        """
        Normalize a Windows path for cross-platform compatibility

        Args:
            path (str): Windows path to normalize

        Returns:
            str: Normalized path
        """
        if not path:
            return ""

        # Replace backslashes with forward slashes
        normalized = path.replace('\\', '/')

        # Handle Windows drive letters (e.g., C:/ -> /c/)
        drive_match = re.match(r'^([A-Za-z]):(.*)', normalized)
        if drive_match:
            drive_letter = drive_match.group(1).lower()
            rest_of_path = drive_match.group(2)
            normalized = f"/{drive_letter}{rest_of_path}"

        return normalized

    def _test_connection(self) -> bool:
        """Test if the current connection is valid"""
        if not self.visio_app:
            return False

        try:
            # Try to access a property that would fail if connection is broken
            _ = self.visio_app.Version
            return True
        except:
            # Connection is invalid or lost
            self.visio_app = None
            return False

    def connect(self, server_name: str = None) -> bool:
        """Connect to an existing Visio instance or create a new one

        Args:
            server_name: Name of the remote server to connect to, None for local

        Returns:
            bool: Success or failure
        """
        if not win32com_available:
            logger.warning("win32com not available. Cannot connect to Visio.")
            return False

        # Store the server name
        self.server_name = server_name

        # If we already have a connection, verify it's still valid
        if self._test_connection():
            return True

        # Reset the connection since it's no longer valid
        self.visio_app = None

        # Check if we're connecting to a remote server
        is_remote = server_name is not None and server_name.strip() != ""

        try:
            # Initialize COM in this thread before attempting to connect
            pythoncom.CoInitialize()

            if is_remote:
                logger.info(f"Attempting to connect to Visio on remote server: {server_name}")

                # For remote connections, we need to use DispatchEx with specific CLSCTX flags
                # CLSCTX_SERVER excludes in-process servers, which is necessary for DCOM
                clsctx = pythoncom.CLSCTX_SERVER & ~pythoncom.CLSCTX_INPROC_SERVER

                try:
                    # Try to connect to a remote Visio instance
                    self.visio_app = win32com.client.DispatchEx(
                        "Visio.Application",
                        server_name,
                        clsctx=clsctx
                    )
                    self.visio_app.Visible = True
                    logger.info(f"Connected to Visio on remote server: {server_name}")
                    return True
                except Exception as e:
                    logger.error(f"Failed to connect to Visio on remote server {server_name}: {str(e)}")
                    self._connect_attempts += 1
                    self.visio_app = None
                    return False
            else:
                # Local connection - try to connect to an existing instance first
                try:
                    self.visio_app = win32com.client.GetActiveObject("Visio.Application")
                    logger.info("Connected to existing local Visio instance")
                    return True
                except Exception as e:
                    logger.warning(f"Could not connect to existing local Visio instance: {str(e)}")

                    # Ensure COM is initialized
                    if not hasattr(pythoncom, '_initialized'):
                        pythoncom.CoInitialize()

                    # No active Visio instance, create a new one
                    self.visio_app = win32com.client.Dispatch("Visio.Application")
                    self.visio_app.Visible = True
                    logger.info("Created new local Visio instance")
                    return True
        except Exception as e2:
            logger.error(f"Failed to connect to Visio: {str(e2)}")
            self._connect_attempts += 1
            self.visio_app = None
            return False

    def is_connected(self) -> bool:
        """Check if connected to Visio"""
        return self._test_connection()

    def is_visio_installed(self) -> bool:
        """Check if Visio is installed on the system

        Returns:
            bool: True if Visio is installed, False otherwise
        """
        if not win32com_available:
            return False

        try:
            # Try to create a Dispatch object for Visio.Application
            # This will succeed if Visio is installed, even if it's not running
            import winreg
            # Check registry for Visio installation
            try:
                winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "Visio.Application")
                return True
            except Exception:
                return False
        except Exception as e:
            logger.error(f"Error checking if Visio is installed: {str(e)}")
            return False

    def launch_visio(self) -> bool:
        """Launch Visio application

        Returns:
            bool: Success or failure
        """
        if not win32com_available:
            logger.warning("win32com not available. Cannot launch Visio.")
            return False

        try:
            # Initialize COM
            pythoncom.CoInitialize()

            # Create a new Visio instance
            self.visio_app = win32com.client.Dispatch("Visio.Application")
            self.visio_app.Visible = True
            logger.info("Launched new Visio instance")
            return True
        except pythoncom.com_error as e:
            # Handle specific COM errors
            hr, msg, exc, _ = e.args
            logger.error(f"COM Error launching Visio: {msg}")
            logger.error(f"Error code: 0x{hr:08x}, Exception info: {exc}")
            self.visio_app = None
            return False
        except Exception as e:
            logger.error(f"Failed to launch Visio: {str(e)}")
            self.visio_app = None
            return False

    def get_open_documents(self) -> List[Dict[str, Any]]:
        """Get list of open Visio documents"""
        documents = []

        # Always verify connection before proceeding
        if not self.is_connected():
            if not self.connect():
                return documents

        try:
            # Check if Documents property is accessible
            doc_count = self.visio_app.Documents.Count

            for i in range(1, doc_count + 1):
                try:
                    doc = self.visio_app.Documents.Item(i)

                    # Skip stencil files (.vss, .vssx, .vssm)
                    # Check if the name has an extension
                    doc_name = doc.Name.lower()
                    if (doc_name.endswith('.vss') or doc_name.endswith('.vssx') or
                        doc_name.endswith('.vssm')):
                        logger.info(f"Skipping stencil file: {doc.Name}")
                        continue

                    # Normalize the path for cross-platform compatibility
                    doc_path = self._normalize_path(doc.Path) if doc.Path else ""
                    doc_full_name = self._normalize_path(doc.FullName) if doc.FullName else ""

                    documents.append({
                        "index": i,
                        "name": doc.Name,
                        "path": doc_path,
                        "full_name": doc_full_name,
                        "document": doc
                    })
                except pythoncom.com_error as e:
                    # Handle specific COM errors
                    hr, msg, exc, _ = e.args
                    logger.error(f"COM Error accessing document at index {i}: {msg}")
                    logger.error(f"Error code: 0x{hr:08x}, Exception info: {exc}")
                    continue
                except Exception as e:
                    logger.error(f"Error accessing document at index {i}: {str(e)}")
                    continue
        except pythoncom.com_error as e:
            # Handle specific COM errors
            hr, msg, exc, _ = e.args
            logger.error(f"COM Error getting documents: {msg}")
            logger.error(f"Error code: 0x{hr:08x}, Exception info: {exc}")
            # Connection might be lost, reset it
            self.visio_app = None
        except Exception as e:
            logger.error(f"Error getting open documents: {str(e)}")
            # Connection might be lost, reset it
            self.visio_app = None

        return documents

    def get_pages_in_document(self, doc_index: int) -> List[Dict[str, Any]]:
        """Get list of pages in a Visio document"""
        pages = []

        # Always verify connection before proceeding
        if not self.is_connected():
            if not self.connect():
                return pages

        try:
            docs = self.get_open_documents()
            if not docs or doc_index < 1 or doc_index > len(docs):
                return pages

            doc = docs[doc_index - 1]["document"]

            for i in range(1, doc.Pages.Count + 1):
                try:
                    page = doc.Pages.Item(i)
                    # Check if this page is a schematic/diagram page (not a background page)
                    is_foreground = page.Background == 0
                    is_schematic = False

                    # Try to determine if this is a schematic page based on name
                    page_name_lower = page.Name.lower()
                    if any(term in page_name_lower for term in ['schem', 'diagram', 'circuit', 'layout']):
                        is_schematic = True

                    pages.append({
                        "index": i,
                        "name": page.Name,
                        "page": page,
                        "is_foreground": is_foreground,
                        "is_schematic": is_schematic
                    })
                except Exception as e:
                    logger.error(f"Error accessing page at index {i}: {str(e)}")
                    continue
        except Exception as e:
            logger.error(f"Error getting pages: {str(e)}")
            # Connection might be lost, reset it
            self.visio_app = None

        return pages

    def get_default_document_page(self) -> Tuple[int, int, bool]:
        """
        Finds the most appropriate default document and page to use

        Returns:
            Tuple[int, int, bool]: (doc_index, page_index, found_valid)
        """
        # Always verify connection before proceeding
        if not self.is_connected():
            if not self.connect():
                return 1, 1, False

        try:
            docs = self.get_open_documents()

            # No documents open
            if not docs:
                return 1, 1, False

            # If only one document is open, use it
            if len(docs) == 1:
                doc_index = 1
                # Get pages in this document
                pages = self.get_pages_in_document(doc_index)

                # No pages in document
                if not pages:
                    return doc_index, 1, False

                # Try to find a schematic page first
                schematic_pages = [p for p in pages if p["is_schematic"] and p["is_foreground"]]
                if schematic_pages:
                    # Use the first schematic page
                    return doc_index, schematic_pages[0]["index"], True

                # Otherwise use the first foreground page
                foreground_pages = [p for p in pages if p["is_foreground"]]
                if foreground_pages:
                    return doc_index, foreground_pages[0]["index"], True

                # Last resort: use the first page
                return doc_index, 1, True

            # Multiple documents open - just return the first doc and first page
            # The UI will handle selection
            return 1, 1, True

        except Exception as e:
            logger.error(f"Error finding default document/page: {str(e)}")
            # Connection might be lost, reset it
            self.visio_app = None
            return 1, 1, False

    def import_shape_to_visio(self, stencil_path: str, shape_name: str,
                              doc_index: int = 1, page_index: int = 1,
                              x_pos: float = 4.0, y_pos: float = 4.0) -> bool:
        """
        Import a shape from a stencil to an open Visio document

        Args:
            stencil_path: Path to the stencil file
            shape_name: Name of the shape to import
            doc_index: Index of the document (1-based)
            page_index: Index of the page (1-based)
            x_pos: X position in inches
            y_pos: Y position in inches

        Returns:
            bool: Success or failure
        """
        # Always verify connection before proceeding
        if not self.is_connected():
            if not self.connect():
                return False

        stencil = None
        try:
            # Get the document and page
            docs = self.get_open_documents()
            if not docs or doc_index < 1 or doc_index > len(docs):
                logger.error(f"Document index {doc_index} out of range")
                return False

            doc = docs[doc_index - 1]["document"]

            # Get the page
            if page_index < 1 or page_index > doc.Pages.Count:
                logger.error(f"Page index {page_index} out of range")
                return False

            page = doc.Pages.Item(page_index)

            # Open the stencil
            try:
                # First try to open as a document stencil
                stencil = self.visio_app.Documents.OpenEx(
                    stencil_path,
                    const.visOpenRO + const.visOpenDocked
                )
            except Exception:
                logger.warning(f"Could not open stencil {stencil_path} as a docked stencil, trying as a normal document")
                try:
                    # Then try to open as a normal stencil
                    stencil = self.visio_app.Documents.Open(stencil_path)
                except Exception as e2:
                    logger.error(f"Failed to open stencil {stencil_path}: {str(e2)}")
                    return False

            # Find the shape in the stencil
            shape_master = None
            for i in range(1, stencil.Masters.Count + 1):
                master = stencil.Masters.Item(i)
                if master.Name == shape_name:
                    shape_master = master
                    break

            if not shape_master:
                logger.error(f"Shape {shape_name} not found in stencil {stencil_path}")
                return False

            # Drop the shape onto the page
            page.Drop(shape_master, x_pos, y_pos)

            logger.info(f"Successfully imported shape {shape_name} to document {doc.Name}, page {page.Name}")
            return True

        except Exception as e:
            logger.error(f"Error importing shape: {str(e)}")
            # Connection might be lost, reset it
            self.visio_app = None
            return False
        finally:
            # Close the stencil if it was opened
            if stencil:
                try:
                    stencil.Close()
                except:
                    pass

    def import_multiple_shapes(self, shapes: List[Dict[str, str]],
                               doc_index: int = 1, page_index: int = 1) -> Tuple[int, int]:
        """
        Import multiple shapes to Visio

        Args:
            shapes: List of dictionaries with 'path' and 'name' keys
            doc_index: Index of the document (1-based)
            page_index: Index of the page (1-based)

        Returns:
            Tuple[int, int]: (successful_count, total_count)
        """
        if not shapes:
            return 0, 0

        # Always verify connection before proceeding
        if not self.is_connected():
            if not self.connect():
                return 0, len(shapes)

        successful = 0
        total = len(shapes)

        # Calculate grid layout
        rows = int(total ** 0.5)  # Square root for grid
        cols = (total + rows - 1) // rows

        # Set up spacing
        x_spacing = 2.0
        y_spacing = 2.0

        # Track already opened stencils to avoid reopening
        opened_stencils = {}

        try:
            # Get the document and page
            docs = self.get_open_documents()
            if not docs or doc_index < 1 or doc_index > len(docs):
                logger.error(f"Document index {doc_index} out of range")
                return 0, total

            doc = docs[doc_index - 1]["document"]

            # Get the page
            if page_index < 1 or page_index > doc.Pages.Count:
                logger.error(f"Page index {page_index} out of range")
                return 0, total

            page = doc.Pages.Item(page_index)

            # Import each shape
            for i, shape_info in enumerate(shapes):
                # Calculate position in grid
                row = i // cols
                col = i % cols

                x_pos = 1.0 + col * x_spacing
                y_pos = 8.0 - row * y_spacing

                try:
                    stencil_path = shape_info["path"]
                    shape_name = shape_info["name"]

                    # Check if we already opened this stencil
                    stencil = opened_stencils.get(stencil_path)

                    if not stencil:
                        # Open the stencil if not already opened
                        try:
                            # First try to open as a document stencil
                            stencil = self.visio_app.Documents.OpenEx(
                                stencil_path,
                                const.visOpenRO + const.visOpenDocked
                            )
                        except Exception:
                            try:
                                # Then try to open as a normal stencil
                                stencil = self.visio_app.Documents.Open(stencil_path)
                            except Exception as e:
                                logger.error(f"Failed to open stencil {stencil_path}: {str(e)}")
                                continue

                        # Save in our dictionary for reuse
                        opened_stencils[stencil_path] = stencil

                    # Find the shape in the stencil
                    shape_master = None
                    for j in range(1, stencil.Masters.Count + 1):
                        master = stencil.Masters.Item(j)
                        if master.Name == shape_name:
                            shape_master = master
                            break

                    if not shape_master:
                        logger.error(f"Shape {shape_name} not found in stencil {stencil_path}")
                        continue

                    # Drop the shape onto the page
                    page.Drop(shape_master, x_pos, y_pos)
                    successful += 1

                except Exception as e:
                    logger.error(f"Error importing shape {shape_name}: {str(e)}")

            return successful, total

        except Exception as e:
            logger.error(f"Error during multiple shape import: {str(e)}")
            # Connection might be lost, reset it
            self.visio_app = None
            return successful, total
        finally:
            # Close all opened stencils
            for path, stencil in opened_stencils.items():
                try:
                    stencil.Close()
                except:
                    pass

    def get_default_document_page(self) -> Tuple[int, int, bool]:
        """Get the default document and page indices

        Returns:
            Tuple[int, int, bool]: (doc_index, page_index, found_valid)
        """
        # Default values
        doc_index = 1
        page_index = 1
        found_valid = False

        # Always verify connection before proceeding
        if not self.is_connected():
            if not self.connect():
                return doc_index, page_index, found_valid

        try:
            # Get open documents
            docs = self.get_open_documents()
            if not docs:
                return doc_index, page_index, found_valid

            # Use the first document
            doc_index = docs[0]['index']

            # Get pages in the document
            pages = self.get_pages_in_document(doc_index)
            if not pages:
                return doc_index, page_index, found_valid

            # Use the first page
            page_index = pages[0]['index']

            found_valid = True
            return doc_index, page_index, found_valid

        except Exception as e:
            logger.error(f"Error getting default document and page: {str(e)}")
            return doc_index, page_index, found_valid

    def create_new_document(self, doc_name: str = "New Document") -> bool:
        """Create a new Visio document

        Args:
            doc_name: Name for the new document

        Returns:
            bool: Success or failure
        """
        # Always verify connection before proceeding
        if not self.is_connected():
            if not self.connect():
                return False

        try:
            # Create a new document
            doc = self.visio_app.Documents.Add("")

            # The document will need to be saved to have a name
            logger.info(f"Created new document: {doc.Name}")
            return True

        except Exception as e:
            logger.error(f"Error creating new document: {str(e)}")
            # Connection might be lost, reset it
            self.visio_app = None
            return False

    def close_document(self, doc_index: int, save_changes: bool = True) -> bool:
        """Close a Visio document

        Args:
            doc_index: Index of the document (1-based)
            save_changes: Whether to save changes before closing

        Returns:
            bool: Success or failure
        """
        # Always verify connection before proceeding
        if not self.is_connected():
            if not self.connect():
                return False

        try:
            # Get open documents
            docs = self.get_open_documents()
            if not docs or doc_index < 1 or doc_index > len(docs):
                return False

            # Get the document
            doc = None
            for d in docs:
                if d['index'] == doc_index:
                    doc = d['document']
                    break

            if not doc:
                return False

            # Close the document
            if save_changes:
                doc.Close()
            else:
                doc.Close(const.visCloseDoNotSaveChanges)

            logger.info(f"Closed document at index {doc_index}")
            return True

        except Exception as e:
            logger.error(f"Error closing document: {str(e)}")
            # Connection might be lost, reset it
            self.visio_app = None
            return False

    def create_new_page(self, doc_index: int, page_name: str = "New Page") -> bool:
        """Create a new page in a Visio document

        Args:
            doc_index: Index of the document (1-based)
            page_name: Name for the new page

        Returns:
            bool: Success or failure
        """
        # Always verify connection before proceeding
        if not self.is_connected():
            if not self.connect():
                return False

        try:
            # Get open documents
            docs = self.get_open_documents()
            if not docs or doc_index < 1 or doc_index > len(docs):
                return False

            # Get the document
            doc = None
            for d in docs:
                if d['index'] == doc_index:
                    doc = d['document']
                    break

            if not doc:
                return False

            # Create a new page
            page = doc.Pages.Add()
            page.Name = page_name

            logger.info(f"Created new page '{page_name}' in document at index {doc_index}")
            return True

        except Exception as e:
            logger.error(f"Error creating new page: {str(e)}")
            # Connection might be lost, reset it
            self.visio_app = None
            return False

    def rename_page(self, doc_index: int, page_index: int, new_name: str) -> bool:
        """Rename a page in a Visio document

        Args:
            doc_index: Index of the document (1-based)
            page_index: Index of the page (1-based)
            new_name: New name for the page

        Returns:
            bool: Success or failure
        """
        # Always verify connection before proceeding
        if not self.is_connected():
            if not self.connect():
                return False

        try:
            # Get open documents
            docs = self.get_open_documents()
            if not docs or doc_index < 1 or doc_index > len(docs):
                return False

            # Get the document
            doc = None
            for d in docs:
                if d['index'] == doc_index:
                    doc = d['document']
                    break

            if not doc:
                return False

            # Get the page
            if page_index < 1 or page_index > doc.Pages.Count:
                return False

            page = doc.Pages.Item(page_index)

            # Rename the page
            old_name = page.Name
            page.Name = new_name

            logger.info(f"Renamed page from '{old_name}' to '{new_name}' in document at index {doc_index}")
            return True

        except Exception as e:
            logger.error(f"Error renaming page: {str(e)}")
            # Connection might be lost, reset it
            self.visio_app = None
            return False

    def save_document(self, doc_index: int) -> bool:
        """Save a Visio document

        Args:
            doc_index: Index of the document (1-based)

        Returns:
            bool: Success or failure
        """
        # Always verify connection before proceeding
        if not self.is_connected():
            if not self.connect():
                return False

        try:
            # Get open documents
            docs = self.get_open_documents()
            if not docs or doc_index < 1 or doc_index > len(docs):
                return False

            # Get the document
            doc = None
            for d in docs:
                if d['index'] == doc_index:
                    doc = d['document']
                    break

            if not doc:
                return False

            # Save the document
            doc.Save()

            logger.info(f"Saved document at index {doc_index}")
            return True

        except Exception as e:
            logger.error(f"Error saving document: {str(e)}")
            # Connection might be lost, reset it
            self.visio_app = None
            return False

    def save_document_as(self, doc_index: int, file_path: str) -> bool:
        """Save a Visio document with a new name

        Args:
            doc_index: Index of the document (1-based)
            file_path: Path to save the document to

        Returns:
            bool: Success or failure
        """
        # Always verify connection before proceeding
        if not self.is_connected():
            if not self.connect():
                return False

        try:
            # Get open documents
            docs = self.get_open_documents()
            if not docs or doc_index < 1 or doc_index > len(docs):
                return False

            # Get the document
            doc = None
            for d in docs:
                if d['index'] == doc_index:
                    doc = d['document']
                    break

            if not doc:
                return False

            # Save the document with a new name
            doc.SaveAs(file_path)

            logger.info(f"Saved document at index {doc_index} as '{file_path}'")
            return True

        except Exception as e:
            logger.error(f"Error saving document as: {str(e)}")
            # Connection might be lost, reset it
            self.visio_app = None
            return False

    def get_shapes_in_page(self, doc_index: int, page_index: int) -> List[Dict[str, Any]]:
        """Get list of shapes in a Visio page

        Args:
            doc_index: Index of the document (1-based)
            page_index: Index of the page (1-based)

        Returns:
            List[Dict[str, Any]]: List of shapes with properties
        """
        shapes = []

        # Always verify connection before proceeding
        if not self.is_connected():
            if not self.connect():
                return shapes

        try:
            # Get open documents
            docs = self.get_open_documents()
            if not docs or doc_index < 1 or doc_index > len(docs):
                return shapes

            # Get the document
            doc = None
            for d in docs:
                if d['index'] == doc_index:
                    doc = d['document']
                    break

            if not doc:
                return shapes

            # Get the page
            if page_index < 1 or page_index > doc.Pages.Count:
                return shapes

            page = doc.Pages.Item(page_index)

            # Get shapes in the page
            for i in range(1, page.Shapes.Count + 1):
                shape_data = {"index": i, "shape": None} # Initialize with index
                try:
                    shape = page.Shapes.Item(i)
                    shape_data["shape"] = shape
                    shape_data["id"] = shape.ID

                    # Get properties with individual error handling
                    try: shape_data["name"] = shape.Name
                    except Exception: shape_data["name"] = f"Unnamed Shape (ID: {shape.ID})"

                    try: shape_data["text"] = shape.Text if hasattr(shape, "Text") else ""
                    except Exception: shape_data["text"] = "[Error Reading Text]"

                    try: shape_data["type"] = shape.Type
                    except Exception: shape_data["type"] = None

                    try: shape_data["master"] = shape.Master.Name if shape.Master else "None"
                    except Exception: shape_data["master"] = "[Error Reading Master]"

                    try: shape_data["width"] = shape.Width
                    except Exception as e_width: 
                        logger.debug(f"Error accessing Width for shape index {i} (ID: {shape.ID}): {e_width}")
                        shape_data["width"] = 0.0

                    try: shape_data["height"] = shape.Height
                    except Exception as e_height:
                        logger.debug(f"Error accessing Height for shape index {i} (ID: {shape.ID}): {e_height}")
                        shape_data["height"] = 0.0

                    try: shape_data["position_x"] = shape.Cells("PinX").Result("")
                    except Exception as e_x:
                        logger.warning(f"Error accessing PinX for shape index {i} (ID: {shape.ID}): {e_x}")
                        shape_data["position_x"] = 0.0

                    try: shape_data["position_y"] = shape.Cells("PinY").Result("")
                    except Exception as e_y:
                        logger.warning(f"Error accessing PinY for shape index {i} (ID: {shape.ID}): {e_y}")
                        shape_data["position_y"] = 0.0

                    shapes.append(shape_data)

                except Exception as e:
                    # Log error for accessing the shape item itself
                    logger.error(f"Critical error accessing shape object at index {i}: {str(e)}")
                    # Append minimal data if possible
                    shape_data["id"] = shape_data.get("id", "[Unknown ID]") # Try to get ID if already fetched
                    shape_data["name"] = "[Error Accessing Shape Object]"
                    shapes.append(shape_data)
                    continue

            return shapes

        except Exception as e:
            logger.error(f"Error getting shapes in page: {str(e)}")
            # Connection might be lost, reset it
            self.visio_app = None
            return shapes

    def select_shape(self, doc_index: int, page_index: int, shape_id: int) -> bool:
        """Select a shape in Visio

        Args:
            doc_index: Index of the document (1-based)
            page_index: Index of the page (1-based)
            shape_id: ID of the shape to select

        Returns:
            bool: Success or failure
        """
        # Always verify connection before proceeding
        if not self.is_connected():
            if not self.connect():
                return False

        try:
            # Get open documents
            docs = self.get_open_documents()
            if not docs or doc_index < 1 or doc_index > len(docs):
                return False

            # Get the document
            doc = None
            for d in docs:
                if d['index'] == doc_index:
                    doc = d['document']
                    break

            if not doc:
                return False

            # Get the page
            if page_index < 1 or page_index > doc.Pages.Count:
                return False

            page = doc.Pages.Item(page_index)

            # Activate the window and page
            doc.Activate()
            page.Activate()

            # Try to find the shape by ID
            try:
                shape = page.Shapes.ItemFromID(shape_id)

                # Clear current selection and select this shape
                self.visio_app.ActiveWindow.Select(shape, const.visSelect)

                logger.info(f"Selected shape with ID {shape_id}")
                return True
            except Exception as e:
                logger.error(f"Error selecting shape with ID {shape_id}: {str(e)}")
                return False

        except Exception as e:
            logger.error(f"Error during shape selection: {str(e)}")
            # Connection might be lost, reset it
            self.visio_app = None
            return False

    def delete_shape(self, doc_index: int, page_index: int, shape_id: int) -> bool:
        """Delete a shape from a Visio page

        Args:
            doc_index: Index of the document (1-based)
            page_index: Index of the page (1-based)
            shape_id: ID of the shape to delete

        Returns:
            bool: Success or failure
        """
        # Always verify connection before proceeding
        if not self.is_connected():
            if not self.connect():
                return False

        try:
            # Get open documents
            docs = self.get_open_documents()
            if not docs or doc_index < 1 or doc_index > len(docs):
                return False

            # Get the document
            doc = None
            for d in docs:
                if d['index'] == doc_index:
                    doc = d['document']
                    break

            if not doc:
                return False

            # Get the page
            if page_index < 1 or page_index > doc.Pages.Count:
                return False

            page = doc.Pages.Item(page_index)

            # Try to find the shape by ID
            try:
                shape = page.Shapes.ItemFromID(shape_id)

                # Delete the shape
                shape.Delete()

                logger.info(f"Deleted shape with ID {shape_id}")
                return True
            except Exception as e:
                logger.error(f"Error deleting shape with ID {shape_id}: {str(e)}")
                return False

        except Exception as e:
            logger.error(f"Error during shape deletion: {str(e)}")
            # Connection might be lost, reset it
            self.visio_app = None
            return False

    def update_shape_text(self, doc_index: int, page_index: int, shape_id: int, new_text: str) -> bool:
        """Update the text of a shape

        Args:
            doc_index: Index of the document (1-based)
            page_index: Index of the page (1-based)
            shape_id: ID of the shape to update
            new_text: New text for the shape

        Returns:
            bool: Success or failure
        """
        # Always verify connection before proceeding
        if not self.is_connected():
            if not self.connect():
                return False

        try:
            # Get open documents
            docs = self.get_open_documents()
            if not docs or doc_index < 1 or doc_index > len(docs):
                return False

            # Get the document
            doc = None
            for d in docs:
                if d['index'] == doc_index:
                    doc = d['document']
                    break

            if not doc:
                return False

            # Get the page
            if page_index < 1 or page_index > doc.Pages.Count:
                return False

            page = doc.Pages.Item(page_index)

            # Try to find the shape by ID
            try:
                shape = page.Shapes.ItemFromID(shape_id)

                # Update the shape text
                shape.Text = new_text

                logger.info(f"Updated text for shape with ID {shape_id}")
                return True
            except Exception as e:
                logger.error(f"Error updating text for shape with ID {shape_id}: {str(e)}")
                return False

        except Exception as e:
            logger.error(f"Error during shape text update: {str(e)}")
            # Connection might be lost, reset it
            self.visio_app = None
            return False

    def move_shape(self, doc_index: int, page_index: int, shape_id: int, x: float, y: float) -> bool:
        """Move a shape to a new position

        Args:
            doc_index: Index of the document (1-based)
            page_index: Index of the page (1-based)
            shape_id: ID of the shape to move
            x: New X position (in page units)
            y: New Y position (in page units)

        Returns:
            bool: Success or failure
        """
        # Always verify connection before proceeding
        if not self.is_connected():
            if not self.connect():
                return False

        try:
            # Get open documents
            docs = self.get_open_documents()
            if not docs or doc_index < 1 or doc_index > len(docs):
                return False

            # Get the document
            doc = None
            for d in docs:
                if d['index'] == doc_index:
                    doc = d['document']
                    break

            if not doc:
                return False

            # Get the page
            if page_index < 1 or page_index > doc.Pages.Count:
                return False

            page = doc.Pages.Item(page_index)

            # Try to find the shape by ID
            try:
                shape = page.Shapes.ItemFromID(shape_id)

                # Get current position
                old_x = shape.Cells("PinX").Result("")
                old_y = shape.Cells("PinY").Result("")

                # Move the shape
                shape.Cells("PinX").Formula = str(x)
                shape.Cells("PinY").Formula = str(y)

                logger.info(f"Moved shape with ID {shape_id} from ({old_x}, {old_y}) to ({x}, {y})")
                return True
            except Exception as e:
                logger.error(f"Error moving shape with ID {shape_id}: {str(e)}")
                return False

        except Exception as e:
            logger.error(f"Error during shape movement: {str(e)}")
            # Connection might be lost, reset it
            self.visio_app = None
            return False

    def resize_shape(self, doc_index: int, page_index: int, shape_id: int, width: float, height: float) -> bool:
        """Resize a shape

        Args:
            doc_index: Index of the document (1-based)
            page_index: Index of the page (1-based)
            shape_id: ID of the shape to resize
            width: New width (in page units)
            height: New height (in page units)

        Returns:
            bool: Success or failure
        """
        # Always verify connection before proceeding
        if not self.is_connected():
            if not self.connect():
                return False

        try:
            # Get open documents
            docs = self.get_open_documents()
            if not docs or doc_index < 1 or doc_index > len(docs):
                return False

            # Get the document
            doc = None
            for d in docs:
                if d['index'] == doc_index:
                    doc = d['document']
                    break

            if not doc:
                return False

            # Get the page
            if page_index < 1 or page_index > doc.Pages.Count:
                return False

            page = doc.Pages.Item(page_index)

            # Try to find the shape by ID
            try:
                shape = page.Shapes.ItemFromID(shape_id)

                # Get current size
                old_width = shape.Cells("Width").Result("")
                old_height = shape.Cells("Height").Result("")

                # Resize the shape
                shape.Cells("Width").Formula = str(width)
                shape.Cells("Height").Formula = str(height)

                logger.info(f"Resized shape with ID {shape_id} from ({old_width} x {old_height}) to ({width} x {height})")
                return True
            except Exception as e:
                logger.error(f"Error resizing shape with ID {shape_id}: {str(e)}")
                return False

        except Exception as e:
            logger.error(f"Error during shape resizing: {str(e)}")
            # Connection might be lost, reset it
            self.visio_app = None
            return False

    def create_basic_shape(self, doc_index: int, page_index: int, shape_type: str, x: float, y: float, width: float, height: float) -> Optional[int]:
        """Create a basic shape on the page

        Args:
            doc_index: Index of the document (1-based)
            page_index: Index of the page (1-based)
            shape_type: Type of shape to create ('rectangle', 'ellipse', 'line', etc.)
            x: X position (in page units)
            y: Y position (in page units)
            width: Width of the shape (in page units)
            height: Height of the shape (in page units)

        Returns:
            Optional[int]: ID of the created shape, or None on failure
        """
        # Always verify connection before proceeding
        if not self.is_connected():
            if not self.connect():
                return None

        try:
            # Get open documents
            docs = self.get_open_documents()
            if not docs or doc_index < 1 or doc_index > len(docs):
                return None

            # Get the document
            doc = None
            for d in docs:
                if d['index'] == doc_index:
                    doc = d['document']
                    break

            if not doc:
                return None

            # Get the page
            if page_index < 1 or page_index > doc.Pages.Count:
                return None

            page = doc.Pages.Item(page_index)

            # Create the shape based on type
            shape = None

            if shape_type.lower() == 'rectangle':
                # Create a rectangle
                shape = page.DrawRectangle(x - width/2, y - height/2, x + width/2, y + height/2)
            elif shape_type.lower() == 'ellipse':
                # Create an ellipse
                shape = page.DrawOval(x - width/2, y - height/2, x + width/2, y + height/2)
            elif shape_type.lower() == 'line':
                # Create a line
                shape = page.DrawLine(x - width/2, y, x + width/2, y)
            elif shape_type.lower() == 'triangle':
                # Create a triangle
                shape = page.DrawQuarterArc(x - width/2, y - height/2, x + width/2, y + height/2, 0)
                # This is not a perfect triangle, but it's a close approximation
            else:
                logger.error(f"Unsupported shape type: {shape_type}")
                return None

            if shape:
                logger.info(f"Created {shape_type} shape with ID {shape.ID}")
                return shape.ID
            else:
                return None

        except Exception as e:
            logger.error(f"Error creating shape: {str(e)}")
            # Connection might be lost, reset it
            self.visio_app = None
            return None

    def align_shapes(self, doc_index: int, page_index: int, shape_ids: List[int], alignment: str) -> bool:
        """Align shapes on the page

        Args:
            doc_index: Index of the document (1-based)
            page_index: Index of the page (1-based)
            shape_ids: List of shape IDs to align
            alignment: Type of alignment ('left', 'center', 'right', 'top', 'middle', 'bottom')

        Returns:
            bool: Success or failure
        """
        # Always verify connection before proceeding
        if not self.is_connected():
            if not self.connect():
                return False

        try:
            # Get open documents
            docs = self.get_open_documents()
            if not docs or doc_index < 1 or doc_index > len(docs):
                return False

            # Get the document
            doc = None
            for d in docs:
                if d['index'] == doc_index:
                    doc = d['document']
                    break

            if not doc:
                return False

            # Get the page
            if page_index < 1 or page_index > doc.Pages.Count:
                return False

            page = doc.Pages.Item(page_index)

            # Need at least 2 shapes to align
            if len(shape_ids) < 2:
                logger.warning("Need at least 2 shapes to align")
                return False

            # Get the shapes
            shapes = []
            for shape_id in shape_ids:
                try:
                    shape = page.Shapes.ItemFromID(shape_id)
                    shapes.append(shape)
                except Exception as e:
                    logger.error(f"Error getting shape with ID {shape_id}: {str(e)}")
                    return False

            # Select the shapes
            window = self.visio_app.ActiveWindow
            window.DeselectAll()
            for shape in shapes:
                window.Select(shape, const.visSelect)

            # Perform the alignment
            if alignment.lower() == 'left':
                self.visio_app.AlignShapes(const.visHorzLeft, const.visAlignNone, True)
            elif alignment.lower() == 'center':
                self.visio_app.AlignShapes(const.visHorzCenter, const.visAlignNone, True)
            elif alignment.lower() == 'right':
                self.visio_app.AlignShapes(const.visHorzRight, const.visAlignNone, True)
            elif alignment.lower() == 'top':
                self.visio_app.AlignShapes(const.visVertTop, const.visAlignNone, True)
            elif alignment.lower() == 'middle':
                self.visio_app.AlignShapes(const.visVertMiddle, const.visAlignNone, True)
            elif alignment.lower() == 'bottom':
                self.visio_app.AlignShapes(const.visVertBottom, const.visAlignNone, True)
            else:
                logger.error(f"Unsupported alignment type: {alignment}")
                return False

            logger.info(f"Aligned {len(shapes)} shapes with {alignment} alignment")
            return True

        except Exception as e:
            logger.error(f"Error aligning shapes: {str(e)}")
            # Connection might be lost, reset it
            self.visio_app = None
            return False

    def change_shape_order(self, doc_index: int, page_index: int, shape_id: int, order_action: str) -> bool:
        """Change the z-order of a shape

        Args:
            doc_index: Index of the document (1-based)
            page_index: Index of the page (1-based)
            shape_id: ID of the shape to change order
            order_action: Order action ('bring_to_front', 'send_to_back', 'bring_forward', 'send_backward')

        Returns:
            bool: Success or failure
        """
        # Always verify connection before proceeding
        if not self.is_connected():
            if not self.connect():
                return False

        try:
            # Get open documents
            docs = self.get_open_documents()
            if not docs or doc_index < 1 or doc_index > len(docs):
                return False

            # Get the document
            doc = None
            for d in docs:
                if d['index'] == doc_index:
                    doc = d['document']
                    break

            if not doc:
                return False

            # Get the page
            if page_index < 1 or page_index > doc.Pages.Count:
                return False

            page = doc.Pages.Item(page_index)

            # Get the shape
            try:
                shape = page.Shapes.ItemFromID(shape_id)
            except Exception as e:
                logger.error(f"Error getting shape with ID {shape_id}: {str(e)}")
                return False

            # Change the z-order
            if order_action.lower() == 'bring_to_front':
                shape.BringToFront()
            elif order_action.lower() == 'send_to_back':
                shape.SendToBack()
            elif order_action.lower() == 'bring_forward':
                shape.BringForward()
            elif order_action.lower() == 'send_backward':
                shape.SendBackward()
            else:
                logger.error(f"Unsupported order action: {order_action}")
                return False

            logger.info(f"Changed z-order of shape with ID {shape_id} ({order_action})")
            return True

        except Exception as e:
            logger.error(f"Error changing shape order: {str(e)}")
            # Connection might be lost, reset it
            self.visio_app = None
            return False

    def search_shapes_in_document(self, doc_index: int, search_term: str) -> List[Dict[str, Any]]:
        """Search for shapes in a document by name or text

        Args:
            doc_index: Index of the document (1-based)
            search_term: Text to search for in shape names or text

        Returns:
            List[Dict[str, Any]]: List of matching shapes with properties
        """
        results = []

        # Always verify connection before proceeding
        if not self.is_connected():
            if not self.connect():
                return results

        try:
            # Get open documents
            docs = self.get_open_documents()
            if not docs or doc_index < 1 or doc_index > len(docs):
                return results

            # Get the document
            doc = None
            for d in docs:
                if d['index'] == doc_index:
                    doc = d['document']
                    break

            if not doc:
                return results

            # Search through all pages in the document
            for page_idx in range(1, doc.Pages.Count + 1):
                try:
                    page = doc.Pages.Item(page_idx)
                    page_name = page.Name

                    # Get all shapes on this page
                    for shape_idx in range(1, page.Shapes.Count + 1):
                        try:
                            shape = page.Shapes.Item(shape_idx)

                            # Check if shape name or text contains the search term
                            shape_name = shape.Name if hasattr(shape, "Name") else ""
                            shape_text = shape.Text if hasattr(shape, "Text") else ""

                            # Case-insensitive search
                            search_term_lower = search_term.lower()
                            if (search_term_lower in shape_name.lower() or
                                search_term_lower in shape_text.lower()):

                                # Get basic shape properties
                                shape_data = {
                                    "id": shape.ID,
                                    "name": shape_name,
                                    "text": shape_text,
                                    "type": shape.Type,
                                    "master": shape.Master.Name if shape.Master else "None",
                                    "width": shape.Width,
                                    "height": shape.Height,
                                    "position_x": shape.Cells("PinX").Result(""),
                                    "position_y": shape.Cells("PinY").Result(""),
                                    "page_index": page_idx,
                                    "page_name": page_name,
                                    "shape": shape  # Store the actual shape object
                                }

                                results.append(shape_data)
                        except Exception as e:
                            logger.error(f"Error accessing shape at index {shape_idx} on page {page_idx}: {str(e)}")
                            continue
                except Exception as e:
                    logger.error(f"Error accessing page at index {page_idx}: {str(e)}")
                    continue

            return results

        except Exception as e:
            logger.error(f"Error searching shapes in document: {str(e)}")
            # Connection might be lost, reset it
            self.visio_app = None
            return results

# Create a singleton instance
visio = VisioIntegration()