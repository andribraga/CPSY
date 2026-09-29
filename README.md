# CPSY

## Setup (macOS & Raspberry Pi OS)

Install [uv](https://docs.astral.sh/uv/) (same command on both):

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Restart the shell (or `source $HOME/.local/bin/env`). On macOS, `brew install uv` also works.

Install dependencies and run:

```sh
uv sync              # creates .venv, installs Python 3.14 if missing, installs from uv.lock
uv run main.py
```

Add a dependency with `uv add <package>`, then commit both `pyproject.toml` and `uv.lock`.