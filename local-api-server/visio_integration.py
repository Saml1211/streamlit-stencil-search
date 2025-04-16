import win32com.client
import pythoncom
import sys
import base64
import tempfile
import os
import traceback # For detailed error logging

# Constants for Visio units and defaults
MM_PER_INCH = 25.4
DEFAULT_TEXT_WIDTH_MM = 50
DEFAULT_TEXT_HEIGHT_MM = 25
DEFAULT_FONT_SIZE_PT = 10
DEFAULT_IMAGE_WIDTH_MM = 50
MAX_IMAGE_WIDTH_MM = 200
PAGE_CENTER_X_MM = 1189 / 2 # Assuming A0 Landscape width
PAGE_CENTER_Y_MM = 841 / 2 # Assuming A0 Landscape height
PLACEMENT_Y_OFFSET_MM = 100 # Place slightly above vertical center


class VisioIntegrationError(Exception):
    """Custom exception for Visio integration errors."""
    pass

def get_visio_app():
    """
    Gets the running Visio Application object or creates a new one.
    Includes basic error handling for COM issues.
    """
    try:
        # Initialize COM for the current thread if not already done
        # This might be necessary if running in threads (e.g., with some web servers)
        # but usually handled by win32com itself. Add if issues arise.
        # pythoncom.CoInitialize() 

        print("Attempting to connect to Visio Application...")
        visio_app = win32com.client.Dispatch("Visio.Application")
        # Optionally make Visio visible if it was started by Dispatch
        # visio_app.Visible = True 
        print("Successfully connected to Visio Application.")
        return visio_app
    except pythoncom.com_error as e:
        # Common COM errors:
        # -2147221021 (0x800401E3): Operation unavailable (Visio not running or accessible?)
        # -2147023174 (0x800706BA): RPC server unavailable (Visio closed during operation?)
        print(f"COM Error connecting to Visio: {e}", file=sys.stderr)
        raise VisioIntegrationError(f"Could not connect to Visio. Ensure Visio is installed and running. Details: {e}")
    except Exception as e:
        print(f"Unexpected error connecting to Visio: {e}", file=sys.stderr)
        raise VisioIntegrationError(f"An unexpected error occurred: {e}")

def import_text_to_visio(text_content, metadata=None):
    """
    Imports text into the active Visio document by creating a shape.
    """
    print(f"Attempting to import text: '{text_content[:50]}...'")
    visio = None
    doc = None
    page = None
    shape = None
    try:
        pythoncom.CoInitialize() # Initialize COM for this thread
        visio = get_visio_app()
        if not visio.ActiveDocument:
            raise VisioIntegrationError("No active document found in Visio.")
        doc = visio.ActiveDocument
        if not doc.ActivePage:
             raise VisioIntegrationError("No active page found in the active document.")
        page = doc.ActivePage

        # Use page dimensions if available, otherwise fallback to A0 defaults for placement
        try:
            page_width_mm = page.PageSheet.CellsU("PageWidth").Result("mm")
            page_height_mm = page.PageSheet.CellsU("PageHeight").Result("mm")
            center_x_mm = page_width_mm / 2
            center_y_mm = page_height_mm / 2
        except Exception: # Fallback if page dimensions aren't accessible
            print("Warning: Could not get page dimensions, using A0 defaults for placement.", file=sys.stderr)
            center_x_mm = PAGE_CENTER_X_MM
            center_y_mm = PAGE_CENTER_Y_MM

        # Calculate placement coordinates (center horizontally, slightly above center vertically)
        # Visio origin (0,0) is bottom-left. Coordinates are for shape center.
        pin_x_mm = center_x_mm
        pin_y_mm = center_y_mm + PLACEMENT_Y_OFFSET_MM

        # Draw a rectangle shape - Visio uses inches for DrawRectangle arguments
        shape = page.DrawRectangle(
            pin_x_mm / MM_PER_INCH - (DEFAULT_TEXT_WIDTH_MM / 2) / MM_PER_INCH, # x1 (left)
            pin_y_mm / MM_PER_INCH - (DEFAULT_TEXT_HEIGHT_MM / 2) / MM_PER_INCH, # y1 (bottom)
            pin_x_mm / MM_PER_INCH + (DEFAULT_TEXT_WIDTH_MM / 2) / MM_PER_INCH, # x2 (right)
            pin_y_mm / MM_PER_INCH + (DEFAULT_TEXT_HEIGHT_MM / 2) / MM_PER_INCH  # y2 (top)
        )

        # Set the text content
        shape.Text = text_content

        # Set initial size using FormulaU (allows units)
        shape.CellsU("Width").FormulaU = f"{DEFAULT_TEXT_WIDTH_MM} mm"
        shape.CellsU("Height").FormulaU = f"{DEFAULT_TEXT_HEIGHT_MM} mm"

        # Set font size
        shape.CellsU("Char.Size").FormulaU = f"{DEFAULT_FONT_SIZE_PT} pt"

        # Attempt to set text block behavior (e.g., auto-fit height - might vary by Visio version)
        # Example: shape.CellsU("VerticalAlign").FormulaU = "1" # Middle align
        # Auto-size might be default or harder to control directly for basic shapes.
        # For now, we rely on the initial size and Visio's default text handling.

        print(f"Successfully imported text. Shape ID: {shape.ID}")
        return {"status": "success", "message": f"Text imported successfully.", "shape_id": shape.ID}

    except VisioIntegrationError as vie:
        print(f"Visio Integration Error during text import: {vie}", file=sys.stderr)
        return {"status": "error", "message": str(vie)}
    except pythoncom.com_error as e:
        hr, msg, exc, arg = e.args
        print(f"COM Error during text import: {e}", file=sys.stderr)
        traceback.print_exc()
        return {"status": "error", "message": f"Visio COM Error (HRESULT: {hr}): {exc[2] if exc else msg}"}
    except Exception as e:
        print(f"Unexpected error during text import: {e}", file=sys.stderr)
        traceback.print_exc()
        return {"status": "error", "message": f"Unexpected error during text import: {e}"}
    finally:
        # Release COM objects if they were assigned
        if shape: shape = None
        if page: page = None
        if doc: doc = None
        if visio: visio = None
        pythoncom.CoUninitialize() # Uninitialize COM for this thread


def import_image_to_visio(base64_image_content, metadata=None):
    """
    Imports an image from a Base64 string into the active Visio document.
    """
    print(f"Attempting to import image: '{base64_image_content[:50]}...'")
    visio = None
    doc = None
    page = None
    shape = None
    temp_file_path = None

    try:
        pythoncom.CoInitialize() # Initialize COM for this thread

        # 1. Decode Base64 and save to temporary file
        if not base64_image_content:
            raise ValueError("No image content provided.")

        img_data = base64_image_content
        # Strip the prefix if present (e.g., "data:image/png;base64,")
        if ',' in base64_image_content:
            header, img_data = base64_image_content.split(',', 1)
            # Try to get suffix from mime type
            try:
                mime_type = header.split(';')[0].split(':')[1]
                suffix = '.' + mime_type.split('/')[1] if '/' in mime_type else '.png'
            except IndexError:
                suffix = '.png' # Default if header parsing fails
        else:
            # Assume raw base64, default to png
            suffix = '.png'

        decoded_image = base64.b64decode(img_data)

        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(decoded_image)
            temp_file_path = temp_file.name
            print(f"Image saved temporarily to: {temp_file_path}")

        # 2. Import into Visio using COM
        visio = get_visio_app()
        if not visio.ActiveDocument:
            raise VisioIntegrationError("No active document found in Visio.")
        doc = visio.ActiveDocument
        if not doc.ActivePage:
            raise VisioIntegrationError("No active page found in the active document.")
        page = doc.ActivePage

        # Use page dimensions if available, otherwise fallback to A0 defaults for placement
        try:
            page_width_mm = page.PageSheet.CellsU("PageWidth").Result("mm")
            page_height_mm = page.PageSheet.CellsU("PageHeight").Result("mm")
            center_x_mm = page_width_mm / 2
            center_y_mm = page_height_mm / 2
        except Exception:
            print("Warning: Could not get page dimensions, using A0 defaults for placement.", file=sys.stderr)
            center_x_mm = PAGE_CENTER_X_MM
            center_y_mm = PAGE_CENTER_Y_MM

        # Import the image file onto the page
        shape = page.Import(temp_file_path)

        # 3. Position and Size the imported shape
        # Calculate placement coordinates (center horizontally, slightly above center vertically)
        pin_x_mm = center_x_mm
        pin_y_mm = center_y_mm + PLACEMENT_Y_OFFSET_MM

        # Set position (PinX, PinY represent the shape's center)
        shape.CellsU("PinX").FormulaU = f"{pin_x_mm} mm"
        shape.CellsU("PinY").FormulaU = f"{pin_y_mm} mm"

        # Set width (Visio typically maintains aspect ratio automatically)
        target_width_mm = DEFAULT_IMAGE_WIDTH_MM
        if metadata and isinstance(metadata.get("user_options"), dict):
            # Example: Allow overriding width via metadata (up to max)
            try:
                req_width = float(metadata["user_options"].get("width_mm", DEFAULT_IMAGE_WIDTH_MM))
                target_width_mm = min(max(req_width, 10), MAX_IMAGE_WIDTH_MM) # Clamp between 10mm and MAX
            except (ValueError, TypeError):
                 pass # Use default if invalid

        shape.CellsU("Width").FormulaU = f"{target_width_mm} mm"

        print(f"Successfully imported image. Shape ID: {shape.ID}")
        return {"status": "success", "message": f"Image imported successfully.", "shape_id": shape.ID}

    except VisioIntegrationError as vie:
        print(f"Visio Integration Error during image import: {vie}", file=sys.stderr)
        return {"status": "error", "message": str(vie)}
    except pythoncom.com_error as e:
        hr, msg, exc, arg = e.args
        print(f"COM Error during image import: {e}", file=sys.stderr)
        traceback.print_exc()
        return {"status": "error", "message": f"Visio COM Error (HRESULT: {hr}): {exc[2] if exc else msg}"}
    except (ValueError, base64.binascii.Error) as decode_error:
         print(f"Error decoding Base64 image data: {decode_error}", file=sys.stderr)
         return {"status": "error", "message": f"Invalid Base64 image data provided: {decode_error}"}
    except Exception as e:
        print(f"Unexpected error during image import: {e}", file=sys.stderr)
        traceback.print_exc()
        return {"status": "error", "message": f"Unexpected error during image import: {e}"}
    finally:
        # 4. Clean up temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                print(f"Temporary file deleted: {temp_file_path}")
            except Exception as e:
                print(f"Error deleting temporary file {temp_file_path}: {e}", file=sys.stderr)

        # Release COM objects if they were assigned
        if shape: shape = None
        if page: page = None
        if doc: doc = None
        if visio: visio = None
        pythoncom.CoUninitialize() # Uninitialize COM for this thread


def check_visio_connection() -> dict:
    """Checks if a connection to the Visio application can be established."""
    try:
        # Try to get existing or create new instance
        visio = get_visio_app()
        if visio:
            print("Visio connection check: Success.")
            try:
                version = visio.Version
                print(f"Visio Version (Check): {version}")
                return {"status": "connected", "message": f"Visio application is running (Version: {version}) and accessible."}
            except pythoncom.com_error as version_error:
                 print(f"Visio connection check: Instance obtained but unresponsive? COM Error: {version_error}")
                 return {"status": "error", "message": f"Visio instance obtained but might be unresponsive. COM Error: {version_error}"}
            except Exception as generic_version_error:
                 print(f"Visio connection check: Instance obtained but unresponsive? Error: {generic_version_error}")
                 return {"status": "error", "message": f"Visio instance obtained but might be unresponsive. Error: {generic_version_error}"}
        else:
             # Should not happen if get_visio_app works as expected
             return {"status": "error", "message": "Failed to get or create Visio instance (get_visio_app returned None)."}

    except VisioIntegrationError as vie:
        print(f"Visio connection check failed: {vie}")
        return {"status": "disconnected", "error_message": str(vie)}
    except Exception as e:
        print(f"Unexpected error during Visio connection check: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error_message": f"An unexpected error occurred: {e}"}


if __name__ == '__main__':
    # Simple test
    print("Running basic Visio connection test...")
    try:
        app = get_visio_app()
        print(f"Visio Application Version: {app.Version}")
        # Try a simple operation
        # result = import_text_to_visio("Test text import")
        # print(f"Test import result: {result}")
    except VisioIntegrationError as e:
        print(f"Test failed: {e}")
    except Exception as e:
         print(f"Unexpected error during test: {e}")