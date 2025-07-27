import json
import yaml
import logging
from datetime import datetime

# Setting up a basic logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DataFusion:
    def __init__(self):
        self.fused_data = []

    def ingest_and_normalize(self, data, data_format, source):
        """
        Ingests data, normalizes it into a standard format, and logs the process.
        """
        try:
            logging.info(f"Ingesting data from '{source}' in '{data_format}' format.")

            # Normalize data into a standard dictionary
            normalized_entry = {
                'timestamp': datetime.now().isoformat(),
                'source': source,
                'payload': self._parse_data(data, data_format)
            }

            # Basic validation
            if not all(k in normalized_entry for k in ['timestamp', 'source', 'payload']):
                raise ValueError("Normalized data is missing required keys.")

            self.fused_data.append(normalized_entry)
            logging.info(f"Successfully ingested and normalized data from '{source}'.")

        except Exception as e:
            logging.error(f"Error processing data from '{source}': {e}")
            raise

    def _parse_data(self, data, data_format):
        """
        Parses data based on its format.
        """
        if data_format == 'json':
            return json.loads(data)
        elif data_format == 'csv':
            # Simple CSV parsing, assuming comma-separated values
            return [line.split(',') for line in data.strip().split('\n')]
        elif data_format == 'xml':
            # This is a placeholder for actual XML parsing logic
            # In a real scenario, a library like xml.etree.ElementTree would be used
            logging.warning("XML parsing is currently a placeholder.")
            return {'xml_content': data}
        else:
            raise ValueError(f"Unsupported data format: {data_format}")

    def get_fused_data(self):
        """
        Returns the current list of fused data entries.
        """
        return self.fused_data

    def clear_data(self):
        """
        Clears all stored data.
        """
        self.fused_data = []
        logging.info("All data has been cleared.")

    def enrich_data(self, enrichment_function):
        """
        Applies a custom function to enrich each data entry.
        """
        for entry in self.fused_data:
            entry['payload'] = enrichment_function(entry['payload'])

    def filter_data(self, filter_function):
        """
        Filters data based on a custom function.
        """
        self.fused_data = [entry for entry in self.fused_data if filter_function(entry)]

    def aggregate_data(self, group_by_key, aggregation_function):
        """
        Aggregates data based on a key and an aggregation function.
        """
        grouped_data = {}
        for entry in self.fused_data:
            key = entry.get(group_by_key)
            if key not in grouped_data:
                grouped_data[key] = []
            grouped_data[key].append(entry['payload'])

        aggregated_data = {}
        for key, values in grouped_data.items():
            aggregated_data[key] = aggregation_function(values)

        return aggregated_data

    def correlate_and_fuse(self, correlation_key):
        """
        Correlates and fuses data from different sources based on a correlation key.
        """
        correlated_data = {}
        for entry in self.fused_data:
            key = entry['payload'].get(correlation_key)
            if key:
                if key not in correlated_data:
                    correlated_data[key] = []
                correlated_data[key].append(entry)

        fused_output = []
        for key, entries in correlated_data.items():
            if len(entries) > 1:
                fused_entry = {
                    'correlation_key': key,
                    'fused_payload': [entry['payload'] for entry in entries],
                    'sources': [entry['source'] for entry in entries],
                    'timestamps': [entry['timestamp'] for entry in entries]
                }
                fused_output.append(fused_entry)

        return fused_output
