import pytest
from unittest import mock
from app.core.visio_integration import VisioIntegration
from app.core.error_utils import VisioUserError
from app.core.logging_utils import MemoryStreamHandler, get_logger

@pytest.fixture
def visio():
    return VisioIntegration()

@pytest.fixture
def mem_log():
    handler = MemoryStreamHandler(capacity=10)
    logger = get_logger("visio_integration")
    if not any(isinstance(h, MemoryStreamHandler) for h in logger.handlers):
        logger.addHandler(handler)
    yield handler
    logger.removeHandler(handler)

def test_visio_not_installed_error(monkeypatch, visio):
    # Simulate pywintypes.com_error with specific hresult
    class FakeComError(Exception):
        def __init__(self):
            self.hresult = -2147221164  # CLASS_E_CLASSNOTAVAILABLE
            self.args = ("fake",)

    monkeypatch.setattr(visio, "is_visio_installed", mock.Mock(side_effect=FakeComError()))
    with pytest.raises(VisioUserError) as excinfo:
        visio.is_visio_installed()
    assert "not installed" in str(excinfo.value).lower()

def test_visio_rpc_unavailable(monkeypatch, visio):
    # Simulate generic exception with RPC message
    monkeypatch.setattr(visio, "connect", mock.Mock(side_effect=Exception("RPC server is unavailable")))
    with pytest.raises(VisioUserError) as excinfo:
        visio.connect()
    assert "unavailable" in str(excinfo.value).lower()

def test_log_capture_for_visio_error(monkeypatch, visio, mem_log):
    # Simulate an error to trigger logging
    monkeypatch.setattr(visio, "launch_visio", mock.Mock(side_effect=Exception("access is denied")))
    try:
        visio.launch_visio()
    except VisioUserError:
        pass
    logs = mem_log.get_latest_logs()
    assert any("access is denied" in l.lower() for l in logs)
    assert any("visio integration error" in l.lower() for l in logs)