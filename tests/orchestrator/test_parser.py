from katana.orchestrator.parser import parse_scenario
import os

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
    steps = parse_scenario(scenario_file)
    assert len(steps) == 2
    assert steps[0]["run"] == "echo 'hello'"
    assert steps[1]["wait"] == 1
    os.remove(scenario_file)
