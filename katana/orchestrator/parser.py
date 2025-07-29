import yaml

def parse_scenario(file_path):
    """
    Parses a scenario file and returns a tree of actions.
    """
    with open(file_path, "r") as f:
        scenario = yaml.safe_load(f)
    return scenario.get("steps", [])
