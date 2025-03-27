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
    
    def connect(self) -> bool:
        """Connect to an existing Visio instance or create a new one"""
        if not win32com_available:
            logger.warning("win32com not available. Cannot connect to Visio.")
            return False
            
        try:
            # Try to connect to an existing Visio instance
            self.visio_app = win32com.client.GetActiveObject("Visio.Application")
            logger.info("Connected to existing Visio instance")
            return True
        except Exception as e:
            try:
                # No active Visio instance, create a new one
                self.visio_app = win32com.client.Dispatch("Visio.Application")
                self.visio_app.Visible = True
                logger.info("Created new Visio instance")
                return True
            except Exception as e2:
                logger.error(f"Failed to connect to Visio: {str(e2)}")
                self._connect_attempts += 1
                return False
    
    def is_connected(self) -> bool:
        """Check if connected to Visio"""
        return self.visio_app is not None
    
    def get_open_documents(self) -> List[Dict[str, Any]]:
        """Get list of open Visio documents"""
        documents = []
        
        if not self.is_connected() and not self.connect():
            return documents
        
        try:
            for i in range(1, self.visio_app.Documents.Count + 1):
                doc = self.visio_app.Documents.Item(i)
                documents.append({
                    "index": i,
                    "name": doc.Name,
                    "path": doc.Path,
                    "full_name": doc.FullName,
                    "document": doc
                })
        except Exception as e:
            logger.error(f"Error getting open documents: {str(e)}")
        
        return documents
    
    def get_pages_in_document(self, doc_index: int) -> List[Dict[str, Any]]:
        """Get list of pages in a Visio document"""
        pages = []
        
        if not self.is_connected() and not self.connect():
            return pages
        
        try:
            docs = self.get_open_documents()
            if doc_index < 1 or doc_index > len(docs):
                return pages
                
            doc = docs[doc_index - 1]["document"]
            
            for i in range(1, doc.Pages.Count + 1):
                page = doc.Pages.Item(i)
                pages.append({
                    "index": i,
                    "name": page.Name,
                    "page": page
                })
        except Exception as e:
            logger.error(f"Error getting pages: {str(e)}")
        
        return pages
    
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
        if not self.is_connected() and not self.connect():
            return False
        
        try:
            # Get the document and page
            docs = self.get_open_documents()
            if doc_index < 1 or doc_index > len(docs):
                logger.error(f"Document index {doc_index} out of range")
                return False
                
            doc = docs[doc_index - 1]["document"]
            
            # Get the page
            if page_index < 1 or page_index > doc.Pages.Count:
                logger.error(f"Page index {page_index} out of range")
                return False
                
            page = doc.Pages.Item(page_index)
            
            # Open the stencil
            stencil = None
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
            shapes: List of dictionaries with 'path', 'name' keys
            doc_index: Index of the document (1-based)
            page_index: Index of the page (1-based)
            
        Returns:
            Tuple[int, int]: (Number of successful imports, total number of shapes)
        """
        if not shapes:
            return 0, 0
            
        if not self.is_connected() and not self.connect():
            return 0, len(shapes)
        
        successful = 0
        total = len(shapes)
        
        # Start at a reasonable position and create a grid
        x_start, y_start = 2.0, 8.0
        x_offset, y_offset = 2.0, -2.0
        shapes_per_row = 5
        
        for i, shape_info in enumerate(shapes):
            # Calculate position (in a grid layout)
            row = i // shapes_per_row
            col = i % shapes_per_row
            x_pos = x_start + (col * x_offset)
            y_pos = y_start + (row * y_offset)
            
            # Import the shape
            if self.import_shape_to_visio(
                shape_info["path"], 
                shape_info["name"],
                doc_index,
                page_index,
                x_pos,
                y_pos
            ):
                successful += 1
        
        return successful, total
    
    def disconnect(self):
        """Disconnect from Visio"""
        self.visio_app = None

# Create a singleton instance
visio = VisioIntegration() 