import pytest
from katana_core.data_fusion import DataFusion
import json

@pytest.fixture
def data_fusion_instance():
    """Provides a clean DataFusion instance for each test."""
    return DataFusion()

def test_ingest_and_normalize_json(data_fusion_instance):
    """
    Tests ingestion and normalization of JSON data.
    """
    json_data = '{"sensor_id": "A123", "value": 42.5}'
    data_fusion_instance.ingest_and_normalize(json_data, 'json', 'sensor-feed')

    fused_data = data_fusion_instance.get_fused_data()
    assert len(fused_data) == 1
    entry = fused_data[0]

    assert entry['source'] == 'sensor-feed'
    assert 'timestamp' in entry
    assert entry['payload'] == json.loads(json_data)

def test_ingest_and_normalize_csv(data_fusion_instance):
    """
    Tests ingestion and normalization of CSV data.
    """
    csv_data = "id,value\n1,10\n2,20"
    data_fusion_instance.ingest_and_normalize(csv_data, 'csv', 'csv-import')

    fused_data = data_fusion_instance.get_fused_data()
    assert len(fused_data) == 1
    entry = fused_data[0]

    assert entry['source'] == 'csv-import'
    assert entry['payload'] == [['id', 'value'], ['1', '10'], ['2', '20']]

def test_ingest_and_normalize_xml_placeholder(data_fusion_instance):
    """
    Tests the placeholder functionality for XML data ingestion.
    """
    xml_data = "<note><to>User</to><from>Jules</from></note>"
    data_fusion_instance.ingest_and_normalize(xml_data, 'xml', 'xml-source')

    fused_data = data_fusion_instance.get_fused_data()
    assert len(fused_data) == 1
    entry = fused_data[0]

    assert entry['source'] == 'xml-source'
    assert entry['payload'] == {'xml_content': xml_data}

def test_unsupported_data_format(data_fusion_instance):
    """
    Tests that an unsupported data format raises a ValueError.
    """
    with pytest.raises(ValueError, match="Unsupported data format: tsv"):
        data_fusion_instance.ingest_and_normalize("data", 'tsv', 'some-source')

def test_clear_data(data_fusion_instance):
    """
    Tests that the clear_data method empties the fused_data list.
    """
    json_data = '{"key": "value"}'
    data_fusion_instance.ingest_and_normalize(json_data, 'json', 'test-source')
    assert len(data_fusion_instance.get_fused_data()) > 0

    data_fusion_instance.clear_data()
    assert len(data_fusion_instance.get_fused_data()) == 0

def test_enrich_data(data_fusion_instance):
    """
    Tests the data enrichment functionality.
    """
    json_data = '{"value": 10}'
    data_fusion_instance.ingest_and_normalize(json_data, 'json', 'test-source')

    def add_ten(payload):
        payload['value'] += 10
        return payload

    data_fusion_instance.enrich_data(add_ten)
    fused_data = data_fusion_instance.get_fused_data()
    assert fused_data[0]['payload']['value'] == 20

def test_filter_data(data_fusion_instance):
    """
    Tests the data filtering functionality.
    """
    json_data1 = '{"value": 10}'
    json_data2 = '{"value": 20}'
    data_fusion_instance.ingest_and_normalize(json_data1, 'json', 'test-source')
    data_fusion_instance.ingest_and_normalize(json_data2, 'json', 'test-source')

    data_fusion_instance.filter_data(lambda entry: entry['payload']['value'] > 15)
    fused_data = data_fusion_instance.get_fused_data()
    assert len(fused_data) == 1
    assert fused_data[0]['payload']['value'] == 20

def test_aggregate_data(data_fusion_instance):
    """
    Tests the data aggregation functionality.
    """
    json_data1 = '{"value": 10, "category": "A"}'
    json_data2 = '{"value": 20, "category": "B"}'
    json_data3 = '{"value": 30, "category": "A"}'
    data_fusion_instance.ingest_and_normalize(json_data1, 'json', 'test-source')
    data_fusion_instance.ingest_and_normalize(json_data2, 'json', 'test-source')
    data_fusion_instance.ingest_and_normalize(json_data3, 'json', 'test-source')

    aggregated_data = data_fusion_instance.aggregate_data('source', lambda payloads: sum(p['value'] for p in payloads))

    assert aggregated_data['test-source'] == 60

def test_correlate_and_fuse_data(data_fusion_instance):
    """
    Tests the data correlation and fusion functionality.
    """
    json_data1 = '{"value": 10, "event_id": "E1"}'
    json_data2 = '{"value": 20, "event_id": "E2"}'
    json_data3 = '{"value": 30, "event_id": "E1"}'
    data_fusion_instance.ingest_and_normalize(json_data1, 'json', 'source1')
    data_fusion_instance.ingest_and_normalize(json_data2, 'json', 'source2')
    data_fusion_instance.ingest_and_normalize(json_data3, 'json', 'source3')

    fused_output = data_fusion_instance.correlate_and_fuse('event_id')

    assert len(fused_output) == 1
    fused_entry = fused_output[0]
    assert fused_entry['correlation_key'] == 'E1'
    assert len(fused_entry['fused_payload']) == 2
    assert fused_entry['fused_payload'][0]['value'] == 10
    assert fused_entry['fused_payload'][1]['value'] == 30
