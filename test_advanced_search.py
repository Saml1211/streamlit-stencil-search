import pytest
from app.core.query_parser import parse_search_query
from modules.Visio_Stencil_Explorer import search_stencils_db

# --- Parser Unit Tests ---

@pytest.mark.parametrize("query,expected", [
    ("router switch", {"and": ["router", "switch"], "or": [], "not": [], "properties": {}}),
    ('"server rack"', {"and": ["server rack"], "or": [], "not": [], "properties": {}}),
    ("router OR switch", {"and": [], "or": ["router", "switch"], "not": [], "properties": {}}),
    ("router | switch", {"and": [], "or": ["router", "switch"], "not": [], "properties": {}}),
    ("cloud -azure", {"and": ["cloud"], "or": [], "not": ["azure"], "properties": {}}),
    ("server NOT dell", {"and": ["server"], "or": [], "not": ["dell"], "properties": {}}),
    ("!legacy", {"and": [], "or": [], "not": ["legacy"], "properties": {}}),
    ("manufacturer:Cisco", {"and": [], "or": [], "not": [], "properties": {"manufacturer": "Cisco"}}),
    ("category:\"network device\"", {"and": [], "or": [], "not": [], "properties": {"category": "network device"}}),
    ("router OR switch -legacy manufacturer:Cisco", {
        "and": [],
        "or": ["router", "switch"],
        "not": ["legacy"],
        "properties": {"manufacturer": "Cisco"}
    }),
])
def test_parse_search_query(query, expected):
    parsed = parse_search_query(query)
    # Only test keys present in expected for flexibility
    for k, v in expected.items():
        assert parsed[k] == v

# --- Backend Integration Tests ---

@pytest.fixture
def dummy_db(monkeypatch):
    # Patch db.search_shapes to return mock data
    test_data = [
        {
            "shape_name": "Router",
            "stencil_name": "Network",
            "description": "A router device",
            "properties": {"manufacturer": "Cisco", "category": "network device"},
        },
        {
            "shape_name": "Switch",
            "stencil_name": "Network",
            "description": "A switch device",
            "properties": {"manufacturer": "HP", "category": "network device", "legacy": "yes"},
        },
        {
            "shape_name": "Firewall",
            "stencil_name": "Security",
            "description": "A firewall device",
            "properties": {"manufacturer": "Palo Alto", "category": "security device"},
        },
        {
            "shape_name": "Server Rack",
            "stencil_name": "Infra",
            "description": "Rack enclosure",
            "properties": {"manufacturer": "HPE", "category": "infrastructure"},
        },
        {
            "shape_name": "Cloud Connector",
            "stencil_name": "Cloud",
            "description": "Connector to cloud",
            "properties": {"category": "cloud", "provider": "Azure"},
        },
    ]
    monkeypatch.setattr(
        "modules.Visio_Stencil_Explorer.StencilDatabase",
        lambda: type("FakeDB", (), {
            "search_shapes": lambda self, search_term, filters, use_fts, limit, directory_filter: test_data,
            "close": lambda self: None
        })()
    )

@pytest.mark.usefixtures("dummy_db")
@pytest.mark.parametrize("query,expected_names", [
    ("router switch", ["Router", "Switch"]),
    ("router OR firewall", ["Router", "Firewall"]),
    ('"server rack"', ["Server Rack"]),
    ("cloud -azure", []),  # "Cloud Connector" has azure in provider, should be excluded
    ("switch -legacy", []),  # "Switch" has legacy property, should be excluded
    ("manufacturer:Cisco", ["Router"]),
    ("category:network", ["Router", "Switch"]),
    ("firewall category:security", ["Firewall"]),
    ("connector -3d", ["Cloud Connector"]),
    ("server OR firewall NOT Palo", ["Server Rack"]),  # "Firewall" has Palo Alto, excluded
])
def test_search_stencils_db(query, expected_names):
    # We use empty filters and directory_filter for all tests
    results = search_stencils_db(query, filters={}, directory_filter=None)
    result_names = sorted([r["shape_name"] for r in results])
    assert sorted(expected_names) == result_names