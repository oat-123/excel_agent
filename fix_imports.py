import os

content_to_prepend = """import json
import re
import requests
import subprocess
import time
import os
from tools.excel_tools import (
    create_excel_file,
    append_row,
    find_duplicates,
    read_excel_file,
    search_excel,
    update_row,
    delete_row,
    copy_data,
    merge_files,
    convert_format,
    summarize_data,
    get_statistics,
    search_excel_files,
    analyze_file_structure,
    detect_patterns_and_relationships,
    ensure_file_path
)
from tools.sheets_tools import search_student, append_student, read_database
from memory.memory_manager import add_skill, get_skill, list_skills, load_skills
from brain.ai_brain import brain

DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'data')

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3"

"""

agent_path = "h:/Users/Asus/Desktop/oat/J.A.R.V.I.S/Excel_Agent/agent.py"
with open(agent_path, "r", encoding="utf-8") as f:
    existing = f.read()

# Remove empty line at top if any
if existing.startswith("\nLAST_USED_FILE"):
    existing = existing.replace("\nLAST_USED_FILE", "LAST_USED_FILE", 1)

with open(agent_path, "w", encoding="utf-8") as f:
    f.write(content_to_prepend + existing)

print("Agent.py fixed!")
