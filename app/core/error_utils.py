"""
Error handling utilities for Visio integration.
Provides a decorator to wrap Visio COM calls and surface user-friendly messages.
"""

import logging
import functools

try:
    import pywintypes
    import win32com.client
    COM_ERRORS_PRESENT = True
except ImportError:
    pywintypes = None
    win32com = None
    COM_ERRORS_PRESENT = False

class VisioUserError(Exception):
    """Exception raised for user-facing Visio errors."""
    def __init__(self, message):
        super().__init__(message)
        self.message = message

def handle_visio_errors(func):
    """
    Decorator to wrap Visio COM integration methods.
    Catches common COM and system errors, logs them, and raises user-friendly errors.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger("visio")
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            # Map known COM errors first (if pywin32 is available)
            msg = None

            if COM_ERRORS_PRESENT:
                if isinstance(exc, pywintypes.com_error):
                    # COM-specific error codes/messages
                    hresult = getattr(exc, 'hresult', None)
                    if hresult in (-2147221164,):  # CLASS_E_CLASSNOTAVAILABLE (Visio not installed)
                        msg = "Microsoft Visio is not installed on this system."
                    elif hresult in (-2147221005,):  # CO_E_SERVER_EXEC_FAILURE (Visio failed to start)
                        msg = "Could not start Microsoft Visio. Please check your installation."
                    else:
                        msg = "A communication error with Microsoft Visio occurred."
                elif isinstance(exc, pywintypes.error):
                    msg = "A Windows API error occurred during Visio operation."
            # Fallbacks for generic errors
            if not msg:
                if "No such interface supported" in str(exc):
                    msg = "Failed to communicate with Visio. Please ensure Visio is running and accessible."
                elif "RPC server is unavailable" in str(exc):
                    msg = "Visio is unavailable (RPC server could not be reached)."
                elif "access is denied" in str(exc).lower():
                    msg = "Access denied when communicating with Microsoft Visio."
                else:
                    msg = "An unexpected error occurred in Visio integration: " + str(exc)

            logger.error(f"Visio Integration Error in {func.__name__}: {exc}", exc_info=True)
            raise VisioUserError(msg) from exc
    return wrapper