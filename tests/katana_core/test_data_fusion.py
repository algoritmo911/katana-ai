import pytest
from katana_core.data_fusion import DataFusion

@pytest.fixture
def data_fusion():
    """Provides a clean DataFusion instance for each test."""
    return DataFusion()

def test_ingest_json(data_fusion):
    json_data = '{"key": "value", "nested": {"a": 1}}'
    data_fusion.ingest(json_data, 'json')
    assert data_fusion.get_data() == {"key": "value", "nested": {"a": 1}}

def test_ingest_yaml(data_fusion):
    yaml_data = """
    key: value
    nested:
      a: 1
    """
    data_fusion.ingest(yaml_data, 'yaml')
    assert data_fusion.get_data() == {"key": "value", "nested": {"a": 1}}

def test_ingest_text(data_fusion):
    text_data = "This is a simple text."
    data_fusion.ingest(text_data, 'text')
    assert data_fusion.get_data() == {"text": "This is a simple text."}

def test_ingest_log(data_fusion):
    log_data = "line 1\nline 2\nline 3"
    data_fusion.ingest(log_data, 'log')
    assert data_fusion.get_data() == {"log": ["line 1", "line 2", "line 3"]}

def test_unsupported_format(data_fusion):
    with pytest.raises(ValueError):
        data_fusion.ingest("some data", "xml")

def test_data_merging(data_fusion):
    json_data = '{"key1": "value1", "nested": {"a": 1}}'
    data_fusion.ingest(json_data, 'json')

    yaml_data = """
    key2: value2
    nested:
      b: 2
    """
    data_fusion.ingest(yaml_data, 'yaml')

    expected_data = {
        "key1": "value1",
        "key2": "value2",
        "nested": {"a": 1, "b": 2}
    }
    assert data_fusion.get_data() == expected_data

def test_list_concatenation(data_fusion):
    data1 = '{"items": ["a", "b"]}'
    data_fusion.ingest(data1, 'json')

    data2 = '{"items": ["c", "d"]}'
    data_fusion.ingest(data2, 'json')

    assert data_fusion.get_data() == {"items": ["a", "b", "c", "d"]}

def test_clear_data(data_fusion):
    json_data = '{"key": "value"}'
    data_fusion.ingest(json_data, 'json')
    assert data_fusion.get_data() is not None
    data_fusion.clear_data()
    assert data_fusion.get_data() == {}
