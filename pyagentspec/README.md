This folder and subfolders contain the code that constitutes the Agent Spec reading/writing python library.

## Build (recommended)

It is advised that you create a Python environment for all modules. In the main folder:

```bash
$ source ./clean-install-dev.sh
```

Then for development, install the assistant in editable mode and the dev dependencies with:

```bash
$ cd pyagentspec
$ ./install-dev.sh
```

## Run tests

To run the tests, please export the URL to the model

```bash
export LLAMA_API_URL=/url/to/some/remote/llm
```
and run the tests with:

```bash
pytest tests
```
