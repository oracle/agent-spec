#!/bin/bash
#
# Copyright © 2026 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

SCRIPT_DIR="$( cd "$( dirname "$0" )" && pwd )"
export SRC_DIR=${SCRIPT_DIR}/src
export REPORT_DIR=${SCRIPT_DIR}/../../conformance_tests_report/benchmarks
export TAU2_DATA_DIR=${SCRIPT_DIR}/tau2-bench/data
export SIMULATIONS_DIR=${TAU2_DATA_DIR}/simulations
: "${OPENAI_API_KEY:=dummy}"
export OPENAI_API_KEY
: "${MODEL_NAME:=GPT-5-mini}"
export MODEL_NAME

if [ $MODEL_NAME == "Llama-3.3-70B-Instruct" ]; then
  export OPENAI_API_BASE=$LLAMA70BV33_API_URL
fi

if [ $MODEL_NAME == "gpt-oss-120b" ]; then
  export OPENAI_API_BASE=$OSS_API_URL
fi

# Only normalize if OPENAI_API_BASE is set and non-empty
if [[ -n "${OPENAI_API_BASE:-}" ]]; then
  # Add http:// prefix if missing (and not already https://)
  if [[ "$OPENAI_API_BASE" != http://* && "$OPENAI_API_BASE" != https://* ]]; then
    OPENAI_API_BASE="http://$OPENAI_API_BASE"
  fi

  # Add /v1 suffix if missing
  if [[ "$OPENAI_API_BASE" != */v1 ]]; then
    OPENAI_API_BASE="${OPENAI_API_BASE%/}/v1"  # trim trailing slash first, then append /v1
  fi

  export OPENAI_API_BASE
fi

get_user_llm() {
  case $MODEL_NAME in
    Llama-3.3-70B-Instruct)
      echo "openai//storage/models/Llama-3.3-70B-Instruct"
      ;;
    gpt-oss-120b)
      echo "openai/openai/gpt-oss-120b"
      ;;
    GPT-5-mini)
      echo "openai/gpt-5-mini"
      ;;
    GPT-5)
      echo "openai/gpt-5"
      ;;
    *)
      echo "Error: MODEL_NAME '$MODEL_NAME' not recognized. Add mapping in get_user_llm()." >&2
      exit 1
      ;;
  esac
}

USER_LLM="$(get_user_llm "${MODEL_NAME}")"

MODEL_NAME="$SCRIPT_DIR/../model_specs/$MODEL_NAME.json"
echo $MODEL_NAME
echo $USER_LLM

if [ ! -d "${REPORT_DIR}" ]; then
  mkdir -p "${REPORT_DIR}"
fi

RUNTIME_NAMES=(
    "WayFlow"
    # "AutoGen"
    # "CrewAI"
    "LangGraph"
    # "AgentFramework"
)
RUNTIME_CLASS_IMPORTS=(
  "wayflowruntime.runtime.WayflowAgentSpecLoader"
  "langgraphruntime.runtime.LanggraphAgentSpecLoader"
)
LABELS=()
for i in "${!RUNTIME_CLASS_IMPORTS[@]}"; do
  RUNTIME_NAME=${RUNTIME_NAMES[$i]}
  RUNTIME_CLASS=${RUNTIME_CLASS_IMPORTS[$i]}
  OUTPUT=${SIMULATIONS_DIR}/${RUNTIME_NAME}$(date +%s)
  echo "Running with runtime class ${RUNTIME_NAME}, model ${MODEL_NAME} and user-llm ${USER_LLM}"
  RUNTIME_CLASS_IMPORT_PATH="${RUNTIME_CLASS}" MODEL_NAME=${MODEL_NAME} \
  python3 ${SRC_DIR}/run_benchmark.py run \
    --domain retail \
    --agent agentspec_agent \
    --user-llm "${USER_LLM}" \
    --num-trials 1 \
    --max-concurrency 10 \
    --max-steps 20 \
    --save-to $OUTPUT
  LABELS+=("${OUTPUT}.json:${RUNTIME_CLASS}")
done
