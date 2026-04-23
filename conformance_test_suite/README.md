# Agent Spec Conformance Test Suite

The Agent Spec conformance test suite is meant to help ensure Agent Spec Runtime correctly
execute Agent Spec configurations. The conformance test suite is easy to run on any
implementation of an Agent Spec Runtime.

## How to use

Set the runtime loader class via the RUNTIME_CLASS_IMPORT_PATH environment variable, then run pytest:

```bash
RUNTIME_CLASS_IMPORT_PATH=python.import.path.to.YourAgentSpecLoaderClass pytest tests/
```

For example to run the test suite on the Langgraph based Agent Spec runtime
```bash
RUNTIME_CLASS_IMPORT_PATH=langgraphruntime.LanggraphAgentSpecLoader pytest tests/
```

- For WayFlow:
```bash
RUNTIME_CLASS_IMPORT_PATH=wayflowruntime.WayflowAgentSpecLoader pytest tests/
```

- For CrewAI:
```bash
RUNTIME_CLASS_IMPORT_PATH=crewairuntime.CrewAIAgentSpecLoader pytest tests/
```

- For AutoGen:
```bash
RUNTIME_CLASS_IMPORT_PATH=autogenruntime.AutogenAgentSpecLoader pytest tests/
```

- For AgentFramework:
```bash
RUNTIME_CLASS_IMPORT_PATH=agentframeworkruntime.AgentFrameworkAgentSpecLoader pytest tests/
```

## Generate a Conformance Test Report (All Runtimes)

Run the test suite across multiple runtimes and generate consolidated reports:

```bash
bash generate_conformance_test_report.sh
```


The above command runs the conformance tests across multiple runtimes, producing Allure and JUnit reports.
This creates a conformance_tests_report folder with the following reports:
  - conformance_tests_report/runtimes_conformance_test_results.html  (HTML dashboard)
  - conformance_tests_report/runtimes_conformance_test_results.csv   (CSV matrix)
  - Allure reports for each individual runtime

For more granular results per sub-modules in the 'Module Breakdown' table, you can increase the value of the **`MODULE_DEPTH`** parameter in the `generate_conformance_test_report.py` file.

## View Allure Reports (Per Runtime)

Use Allure to serve the report for a specific runtime:

```bash
allure serve conformance_tests_report/allure-results-WayFlow
allure serve conformance_tests_report/allure-results-AutoGen
allure serve conformance_tests_report/allure-results-CrewAI
allure serve conformance_tests_report/allure-results-LangGraph
```
