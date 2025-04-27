import threading
from typing import Callable, Any, Optional


class DebounceSearch:
    """
    Helper for debouncing function calls, such as search input handlers.
    Starts/restarts a Timer upon each call, only executing the function after no further calls for 'delay' seconds.
    """

    def __init__(self, function: Callable[..., Any], delay: float = 0.5):
        self.function = function
        self.delay = delay
        self._timer: Optional[threading.Timer] = None
        self._args = ()
        self._kwargs = {}

    def call(self, *args, **kwargs):
        """
        Schedule a debounced call to the function.
        Subsequent calls before delay expiry will reset the timer.
        """
        self._args = args
        self._kwargs = kwargs
        if self._timer is not None:
            self._timer.cancel()
        self._timer = threading.Timer(self.delay, self._run)
        self._timer.start()

    def _run(self):
        self.function(*self._args, **self._kwargs)
        self._timer = None

    def cancel(self):
        """Cancel any scheduled function call."""
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None