ximport pytest
import streamlit as st
from modules import Visio_Stencil_Explorer

@pytest.fixture(autouse=True)
def clear_session_state():
    st.session_state.clear()

def run_basic_stencil_search(monkeypatch):
    # Mock stencil db search to return dummy shapes
    monkeypatch.setattr(
        Visio_Stencil_Explorer, "search_stencils_db",
        lambda search_term, filters, directory_filter=None: [
            {"shape": "Rect", "stencil_name": "Basic Shapes", "stencil_path": "basic.vssx", "shape_id": "S1"}
        ]
    )
    # Mock document results to return nothing
    monkeypatch.setattr(
        Visio_Stencil_Explorer, "search_current_document",
        lambda search_term: []
    )
    # Set relevant session state
    st.session_state["current_search_term"] = "Rect"
    st.session_state["search_history"] = []
    st.session_state["show_favorites_toggle"] = False
    st.session_state["search_in_document"] = False
    # Required filter keys
    for key in [
        "filter_date_start", "filter_date_end", "filter_min_size", "filter_max_size",
        "filter_min_shapes", "filter_max_shapes", "filter_min_width", "filter_max_width",
        "filter_min_height", "filter_max_height", "filter_has_properties",
        "filter_property_name", "filter_property_value", "search_result_limit"
    ]:
        st.session_state[key] = None if "date" in key else 0
    st.session_state["search_result_limit"] = 100
    # Run search
    Visio_Stencil_Explorer.perform_search()

def run_stencil_and_doc_search(monkeypatch):
    # Mock stencil db search to return dummy shapes
    monkeypatch.setattr(
        Visio_Stencil_Explorer, "search_stencils_db",
        lambda search_term, filters, directory_filter=None: [
            {"shape": "Rect", "stencil_name": "Basic Shapes", "stencil_path": "basic.vssx", "shape_id": "S1"}
        ]
    )
    # Mock document search to return a dummy shape
    monkeypatch.setattr(
        Visio_Stencil_Explorer, "search_current_document",
        lambda search_term: [
            {"shape_name": "DocShape", "stencil_name": "Document 1", "stencil_path": "visio_document_1_1", "shape_id": "D1", "is_document_shape": True}
        ]
    )
    st.session_state["current_search_term"] = "Shape"
    st.session_state["search_history"] = []
    st.session_state["show_favorites_toggle"] = False
    st.session_state["search_in_document"] = True
    for key in [
        "filter_date_start", "filter_date_end", "filter_min_size", "filter_max_size",
        "filter_min_shapes", "filter_max_shapes", "filter_min_width", "filter_max_width",
        "filter_min_height", "filter_max_height", "filter_has_properties",
        "filter_property_name", "filter_property_value", "search_result_limit"
    ]:
        st.session_state[key] = None if "date" in key else 0
    st.session_state["search_result_limit"] = 100
    Visio_Stencil_Explorer.perform_search()

def test_result_source_tagging(monkeypatch):
    run_basic_stencil_search(monkeypatch)
    results = st.session_state["search_results"]
    assert len(results) == 1
    assert all(r.get("result_source") == "stencil_directory" for r in results)

    run_stencil_and_doc_search(monkeypatch)
    results = st.session_state["search_results"]
    assert len(results) == 2
    sources = [r.get("result_source") for r in results]
    assert "stencil_directory" in sources
    assert "visio_document" in sources

def test_tab_group_counts(monkeypatch):
    run_stencil_and_doc_search(monkeypatch)
    results = st.session_state["search_results"]
    stencil = [r for r in results if r.get("result_source") == "stencil_directory"]
    document = [r for r in results if r.get("result_source") == "visio_document"]
    assert len(stencil) == 1
    assert len(document) == 1

    # Only stencil mode
    run_basic_stencil_search(monkeypatch)
    results = st.session_state["search_results"]
    stencil = [r for r in results if r.get("result_source") == "stencil_directory"]
    document = [r for r in results if r.get("result_source") == "visio_document"]
    assert len(stencil) == 1
    assert len(document) == 0