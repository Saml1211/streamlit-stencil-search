import win32com.client
import pythoncom
import sys

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
    Placeholder function to import text into the active Visio document.
    """
    print(f"Attempting to import text: '{text_content[:50]}...'")
    try:
        visio = get_visio_app()
        # TODO: Implement actual shape creation and text insertion logic
        # Example (needs refinement):
        # doc = visio.ActiveDocument
        # page = doc.Pages.Item(1) # Or ActivePage
        # shape = page.DrawRectangle(1, 1, 3, 2) # Placeholder coordinates
        # shape.Text = text_content
        print("Placeholder: Would insert text into Visio here.")
        return {"status": "success", "message": "Text imported (stub)", "shape_id": "real_text_shape_1"}
    except VisioIntegrationError as vie:
        return {"status": "error", "message": str(vie)}
    except pythoncom.com_error as e:
         print(f"COM Error during text import: {e}", file=sys.stderr)
         return {"status": "error", "message": f"Visio COM error during import: {e}"}
    except Exception as e:
        print(f"Unexpected error during text import: {e}", file=sys.stderr)
        return {"status": "error", "message": f"Unexpected error during import: {e}"}


def import_image_to_visio(base64_image_content, metadata=None):
    """
    Placeholder function to import an image into the active Visio document.
    """
    print(f"Attempting to import image: '{base64_image_content[:50]}...'")
    # TODO: Need to handle Base64 decoding and saving to a temp file for Visio import
    # For now, just a placeholder
    try:
        visio = get_visio_app()
        # TODO: Implement actual image import logic (e.g., save base64 to temp file, then page.Import())
        print("Placeholder: Would import image into Visio here.")
        return {"status": "success", "message": "Image imported (stub)", "shape_id": "real_image_shape_1"}
    except VisioIntegrationError as vie:
        return {"status": "error", "message": str(vie)}
    except pythoncom.com_error as e:
         print(f"COM Error during image import: {e}", file=sys.stderr)
         return {"status": "error", "message": f"Visio COM error during import: {e}"}
    except Exception as e:
        print(f"Unexpected error during image import: {e}", file=sys.stderr)
        return {"status": "error", "message": f"Unexpected error during import: {e}"}


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