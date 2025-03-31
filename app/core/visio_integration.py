import os
import sys
import logging
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
    
    def connect(self) -> bool:
        """Connect to an existing Visio instance or create a new one"""
        if not win32com_available:
            logger.warning("win32com not available. Cannot connect to Visio.")
            return False
        
        # If we already have a connection, verify it's still valid
        if self._test_connection():
            return True
            
        # Reset the connection since it's no longer valid
        self.visio_app = None
            
        try:
            # Initialize COM in this thread before attempting to connect
            pythoncom.CoInitialize()
            
            # Try to connect to an existing Visio instance
            self.visio_app = win32com.client.GetActiveObject("Visio.Application")
            logger.info("Connected to existing Visio instance")
            return True
        except Exception as e:
            logger.warning(f"Could not connect to existing Visio instance: {str(e)}")
            try:
                # Ensure COM is initialized
                if not hasattr(pythoncom, '_initialized'):
                    pythoncom.CoInitialize()
                
                # No active Visio instance, create a new one
                self.visio_app = win32com.client.Dispatch("Visio.Application")
                self.visio_app.Visible = True
                logger.info("Created new Visio instance")
                return True
            except Exception as e2:
                logger.error(f"Failed to connect to Visio: {str(e2)}")
                self._connect_attempts += 1
                self.visio_app = None
                return False
    
    def is_connected(self) -> bool:
        """Check if connected to Visio"""
        return self._test_connection()
    
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
                        
                    documents.append({
                        "index": i,
                        "name": doc.Name,
                        "path": doc.Path,
                        "full_name": doc.FullName,
                        "document": doc
                    })
                except Exception as e:
                    logger.error(f"Error accessing document at index {i}: {str(e)}")
                    continue
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

# Create a singleton instance
visio = VisioIntegration() 