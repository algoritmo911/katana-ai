from katana.orchestrator.parser import parse_scenario
import os

from katana.orchestrator.context import Context

def test_parse_scenario():
    """
    Test parsing a scenario file.
    """
    scenario_file = "test_scenario.yml"
    with open(scenario_file, "w") as f:
        f.write("""
name: Test Scenario
steps:
  - run: "echo 'hello'"
  - wait: 1
""")
    context = Context()
    scenario = parse_scenario(scenario_file, context)
    steps = scenario.get("steps", [])
    assert len(steps) == 2
    assert steps[0]["run"] == "echo 'hello'"
    assert steps[1]["wait"] == 1
    os.remove(scenario_file)

def test_parse_scenario_with_variables():
    """
    Test parsing a scenario file with variables.
    """
    scenario_file = "test_scenario_with_variables.yml"
    with open(scenario_file, "w") as f:
        f.write("""
name: Test Scenario
vars:
  message: "hello world"
steps:
  - run: "echo '{{ message }}'"
""")
    context = Context()
    context.set_env("message", "hello world")
    scenario = parse_scenario(scenario_file, context)
    steps = scenario.get("steps", [])
    assert len(steps) == 1
    assert steps[0]["run"] == "echo 'hello world'"
    os.remove(scenario_file)
