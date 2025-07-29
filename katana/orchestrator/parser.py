import yaml
from jinja2 import Template

def parse_scenario(file_path, context):
    """
    Parses a scenario file and returns a tree of actions.
    """
    with open(file_path, "r") as f:
        raw_scenario = f.read()

    template = Template(raw_scenario)
    rendered_scenario = template.render(context.env)

    scenario = yaml.safe_load(rendered_scenario)

    # In a real implementation, we would do more validation here.
    return scenario
