import json
import yaml

class DataFusion:
    def __init__(self):
        self.internal_data = {}

    def ingest(self, data, data_format):
        """
        Ingests data in a specified format, parses it, and merges it with the internal data model.
        """
        try:
            if data_format == 'json':
                parsed_data = json.loads(data)
            elif data_format == 'yaml':
                parsed_data = yaml.safe_load(data)
            elif data_format == 'text':
                parsed_data = {'text': data}
            elif data_format == 'log':
                # For simplicity, we'll treat each line as a separate entry in a list
                parsed_data = {'log': data.splitlines()}
            else:
                raise ValueError(f"Unsupported data format: {data_format}")

            self._merge_data(parsed_data)
        except Exception as e:
            # Handle parsing errors
            print(f"Error ingesting data in {data_format} format: {e}")
            # Optionally, re-raise or handle more gracefully
            raise

    def _merge_data(self, new_data):
        """
        Merges new data with the existing internal data.
        A simple recursive merge for dictionaries.
        """
        for key, value in new_data.items():
            if key in self.internal_data and isinstance(self.internal_data[key], dict) and isinstance(value, dict):
                self._recursive_merge(self.internal_data[key], value)
            elif key in self.internal_data and isinstance(self.internal_data[key], list) and isinstance(value, list):
                self.internal_data[key].extend(value)
            else:
                self.internal_data[key] = value

    def _recursive_merge(self, base, new):
        """
        Recursively merges two dictionaries.
        """
        for key, value in new.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._recursive_merge(base[key], value)
            elif key in base and isinstance(base[key], list) and isinstance(value, list):
                base[key].extend(value)
            else:
                base[key] = value

    def get_data(self):
        """
        Returns the current state of the internal data model.
        """
        return self.internal_data

    def clear_data(self):
        """
        Clears the internal data model.
        """
        self.internal_data = {}
