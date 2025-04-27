import os
import json
import tempfile
import pytest

from app.core.preferences import UserPreferences, _DEFAULTS

def make_prefs(tmp_path):
    file_path = os.path.join(tmp_path, "prefs.json")
    return UserPreferences(file_path=file_path), file_path

def test_save_and_load_round_trip(tmp_path):
    prefs, file_path = make_prefs(tmp_path)
    prefs.set("document_search", False)
    prefs.set("results_per_page", 42)
    prefs.save()

    # Load new instance, should read saved values
    prefs2 = UserPreferences(file_path=file_path)
    assert prefs2.get("document_search") is False
    assert prefs2.get("results_per_page") == 42

def test_defaults_when_file_missing(tmp_path):
    # File does not exist
    file_path = os.path.join(tmp_path, "prefs_missing.json")
    if os.path.exists(file_path):
        os.remove(file_path)
    prefs = UserPreferences(file_path=file_path)
    for k, v in _DEFAULTS.items():
        assert prefs.get(k) == v

def test_defaults_when_file_corrupt(tmp_path):
    # Write corrupt JSON
    file_path = os.path.join(tmp_path, "prefs_corrupt.json")
    with open(file_path, "w") as f:
        f.write("{ this is not json }")
    prefs = UserPreferences(file_path=file_path)
    for k, v in _DEFAULTS.items():
        assert prefs.get(k) == v

def test_reset_restores_defaults(tmp_path):
    prefs, file_path = make_prefs(tmp_path)
    prefs.set("fts", False)
    prefs.save()
    prefs.set("fts", True)  # Change in memory, not saved
    prefs.reset()
    for k, v in _DEFAULTS.items():
        assert prefs.get(k) == v

def test_only_known_keys_are_kept(tmp_path):
    prefs, file_path = make_prefs(tmp_path)
    # Simulate file with extra key
    with open(file_path, "w") as f:
        json.dump({"fts": False, "extra_key": 123}, f)
    prefs = UserPreferences(file_path=file_path)
    assert prefs.get("fts") == False
    assert "extra_key" not in prefs._prefs

@pytest.fixture
def tmp_path(tmp_path_factory):
    # On some CI, tmp_path is not available as a function arg to test functions
    return tmp_path_factory.mktemp("prefs")