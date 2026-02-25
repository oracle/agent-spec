# Agent Spec Conformance Test Suite - Tau2Bench Benchmark

This directory contains the necessary elements to run the Tau2 Benchmark on all the Agent Spec runtimes and build a detailed report.

## How to use

Run `install-dev.sh` in this folder. This will:
- Clone the Tau2Bench repo from source
- Add the Agent Spec agent to the repo's agents
- Build and install it from source

You will need to choose a model to run the benchmark on. These are set by exporting the `MODEL_NAME` variable
to the name of a model in the `benchmarks/model_specs` folder, for example `Llama-3.3-70B-Instruct`.
Subsequently, you can run `run.sh`.
This will run the benchmark on each adapter by running the `run_benchmark.py` source, which patches
some small sections of Tau2 to allow for Agent Spec Agent registration.
