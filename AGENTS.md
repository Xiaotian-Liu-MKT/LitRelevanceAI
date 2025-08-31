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
- The CSV analysis tab renders results in a `ttk.Treeview` with title, relevance, and analysis columns, supports exporting results, and opens full analyses on double-click.
- The abstract screening tab loads questions from `configs/questions/abstract.yaml`, provides an editor for yes/no and open questions, logs model summaries in a read-only area, allows cancelling with a stop button, and exports the DataFrame to CSV or Excel.
- The PDF screening tab lists PDFs from a chosen folder with matched metadata and per-file status, accepts research question, criteria, and output type inputs, supports a metadata-only check mode, and offers to open the output directory when finished.
