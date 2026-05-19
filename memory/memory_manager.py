import json
import os

MEMORY_FILE = "memory/skills.json"


def ensure_memory_file():
    os.makedirs("memory", exist_ok=True)

    if not os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)


ensure_memory_file()


def load_skills():
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            if not content.strip():
                return {}
            return json.loads(content)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_skills(skills):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(skills, f, ensure_ascii=False, indent=2)


def add_skill(command_name, workflow):
    skills = load_skills()
    skills[command_name] = workflow
    save_skills(skills)

    return {
        "status": "success",
        "message": f"Saved skill: {command_name}"
    }


def get_skill(command_name):
    skills = load_skills()
    return skills.get(command_name)


def list_skills():
    skills = load_skills()
    return {
        "status": "success",
        "skills": list(skills.keys())
    }