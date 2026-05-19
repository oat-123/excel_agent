# Copilot instructions for Excel_Agent

## Build / Setup
- Install dependencies:
  - python -m pip install -r requirements.txt
- Python requirement: >= 3.11 (configured in pyproject.toml)

## Run commands (common tasks)
- Run web app (development):
  - python app.py
  - Or set FLASK_DEBUG=1 and run python app.py (app reads FLASK_DEBUG)
- Run a single query/script:
  - Run a one-off command through agent: python run_query.py "your command"
  - Or place a query in `query.txt` and run: python run_search.py
  - `search_name.py` is a helper script that reads sheet data and writes search_results.json

## Tests and Linting
- No automated test suite or linter is present in the repo root.
- Type checking configuration present in pyproject.toml under [tool.basedpyright]. To run type checks if you add pyright or other tooling:
  - npm i -g pyright
  - pyright

## High-level architecture
- app.py — Flask front-end and HTTP endpoints. Responsible for uploads, command endpoint (/command), and exposing brain status.
- agent.py — Core command-processing surface (process_command). Other scripts call into process_command for CLI automation.
- tools/ — Excel and sheet utilities (parsing, analysis, helpers for upload pipeline).
- brain/ — AI "brain" components (AIBrain wrapper, knowledge graph, context memory). Knowledge persisted under brain/ (e.g., brain/knowledge_graph.json).
- data/ — Default storage for uploaded files and derived artifacts (uploads/ subfolder used for incoming files).
- run_query.py / run_search.py / search_name.py — small runner scripts used for scripted queries and searches; useful for reproducing single-command runs.

## Key conventions and patterns
- UTF-8-first: several scripts force stdin/stdout encoding to UTF-8 to support Thai text. Preserve UTF-8 when adding scripts or logs.
- Thai sheet schema: schema.py defines SCHEMA_INDEX mapping using Thai column headers. Sheet-parsing utilities expect header names matching that mapping.
- process_command contract: functions that call process_command expect a dict-like result with at least `status` ("success"/"error") and `message` or `response`. Tests or callers should rely on that shape.
- Upload learning pipeline: POST /upload saves the file to data/ then runs analyze_file_structure(...) and learn_from_file_content(..., brain). Keep those hooks when changing upload flow.
- Environment variables used:
  - DATA_FOLDER (default: data)
  - FLASK_DEBUG (controls app.run debug/reloader)
- File size limits: app sets MAX_CONTENT_LENGTH = 16MB for uploads — adjust if larger uploads are required.

## Integrations and AI-config artifacts
- No special AI assistant configuration files found (CLAUDE.md, AGENTS.md, .cursorrules, .windsurfrules, CONVENTIONS.md, AIDER_CONVENTIONS.md, .clinerules). If adding assistant-specific guidance, place it as one of those files and this document will be updated.

## Useful quick examples
- Install and run the server locally:
  - python -m pip install -r requirements.txt
  - python app.py
- Run a single CLI command through the agent:
  - python run_query.py "Summarize the uploaded sheet"
- Produce a quick search for sample names:
  - python search_name.py

---
Generated from pyproject.toml, requirements.txt, app.py, run_query.py, run_search.py, search_name.py, and schema.py. Keep this file up-to-date when adding tests, linters, or additional assistant configs.
