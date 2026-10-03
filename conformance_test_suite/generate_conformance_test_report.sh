#!/bin/bash
#
# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

# Run conformance tests across multiple runtimes, producing Allure and JUnit reports.
# Prerequisites (verify per your environment):
#   - Pytest + allure-pytest: pip install pytest allure-pytest
#   - Allure CLI (optional for serving/generating reports): brew install allure (macOS) or via your OS package manager

# Check required tools
command -v pytest >/dev/null 2>&1 || { echo "pytest not found. Please install it in your environment."; exit 1; }
# Verify pytest has the allure plugin (provides --alluredir)
if ! pytest --help 2>/dev/null | grep -q -- '--alluredir'; then
  echo "pytest is installed but the allure plugin is missing."
  echo "Install it via: pip install allure-pytest (or pip install -e .)"
  exit 1
fi
# allure is optional for report serving/generation; only warn if missing
if ! command -v allure >/dev/null 2>&1; then
  echo "Warning: allure CLI not found. You can still generate allure-results with pytest,"
  echo "but you won't be able to serve/generate HTML reports via 'allure'."
fi

# Output directories
REPORT_DIR="conformance_tests_report"
mkdir -p "${REPORT_DIR}"


# Shared pytest options
PYTEST_COMMON_OPTS=(
  -p no:warnings
  tests/
)

PYTEST_TIMEOUT_SECS="${PYTEST_TIMEOUT_SECS:-}"

# If the timeout variable is specified, then add --timeout=PYTEST_TIMEOUT_SECS to the pytest command
PYTEST_TIMEOUT_ARGS=()
if [[ -n "${PYTEST_TIMEOUT_SECS}" ]]; then
  PYTEST_TIMEOUT_ARGS=("--timeout=${PYTEST_TIMEOUT_SECS}")
fi

# Runtimes to test: name|RUNTIME_CLASS_IMPORT_PATH
RUNTIMES=(
  "WayFlow|wayflowruntime.WayflowAgentSpecLoader"
  "AutoGen|autogenruntime.AutogenAgentSpecLoader"
  "CrewAI|crewairuntime.CrewAIAgentSpecLoader"
  "LangGraph|langgraphruntime.LanggraphAgentSpecLoader"
  "AgentFramework|agentframeworkruntime.AgentFrameworkAgentSpecLoader"
)

echo "Starting test runs..."
for entry in "${RUNTIMES[@]}"; do
  name="${entry%%|*}"
  loader="${entry##*|}"

  # Try to import the loader class to check installation
  if ! python -c "from ${loader%.*} import ${loader##*.}" 2>/dev/null; then
    echo "==> WARNING: Skipping ${name} (${loader}): module/class is not installed or importable."
    continue
  fi

  echo "==> Running for runtime: ${name} (${loader})"

  export RUNTIME_CLASS_IMPORT_PATH="${loader}"

  # Allure results
  allure_dir="${REPORT_DIR}/allure-results-${name}"
  # JUnit XML report
  junit_xml="${REPORT_DIR}/report_${name}.xml"

  pytest "${PYTEST_TIMEOUT_ARGS[@]}" --alluredir="${allure_dir}" --junitxml="${junit_xml}" "${PYTEST_COMMON_OPTS[@]}"

  echo "==> Completed: ${name}"
done

echo
echo "All test runs finished."
echo "JUnit XML reports are in: ${REPORT_DIR}/report_*.xml"
echo "Allure result directories are in: ${REPORT_DIR}/allure-results-*/"
echo

# Combine all JUnit XML files into a final summary report
if [[ -f "generate_conformance_test_report.py" ]]; then
  echo "Combining JUnit XML reports..."
  python generate_conformance_test_report.py
else
  echo "Note: generate_conformance_test_report.py not found; skipping summary combination."
fi

echo "Done."
