# AGENTS

## Development
- Install dependencies with `python -m pip install -e .`.
- Run `python -m litrx --help` to ensure the command line interface loads.
- Run `pytest` before committing.

## Conventions
- Prefer `rg` for searching the repository.
- Keep documentation in both `README.md` and `Chinese_README.md` up to date with any CLI or packaging changes.
- Use the shared `config` and `AIClient` utilities instead of reimplementing configuration loading or model calls.
- When modifying the GUI, use `BaseWindow` for shared controls and add new tabs under `litrx/gui/tabs/`, registering them with `LitRxApp`.
