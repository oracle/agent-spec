# Agent Spec - CTS Benchmarks

Every example can be run by installing the latest version of `pyagentspec` and `wayflow`.
They can be installed with:

```bash
pip install "pyagentspec[langgraph,wayflow]@git+https://github.com/oracle/agent-spec@main#subdirectory=pyagentspec"
```

Follow the instructions in the tau2-bench folder to install the requirements (i.e., run the `install-dev.sh` script).

To select which model to use, put the file name of the model of your choice in the `MODEL_NAME` env variable:
- `GPT-5`
- `GPT-5-mini`
