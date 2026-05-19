import json
import os
import time
from collections import Counter

CONTEXT_FILE = "brain/context_memory.json"

def ensure_context_file():
    os.makedirs("brain", exist_ok=True)
    if not os.path.exists(CONTEXT_FILE):
        with open(CONTEXT_FILE, "w", encoding="utf-8") as f:
            json.dump({"contexts": [], "patterns": {}, "user_preferences": {}}, f, ensure_ascii=False)

ensure_context_file()

def load_context():
    with open(CONTEXT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_context(data):
    with open(CONTEXT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_interaction(user_input, action, result):
    data = load_context()
    data["contexts"].append({
        "user_input": user_input,
        "action": action,
        "result": result.get("status", "unknown"),
        "timestamp": time.time()
    })
    if len(data["contexts"]) > 100:
        data["contexts"] = data["contexts"][-50:]
    save_context(data)

def learn_pattern(user_input, action):
    data = load_context()
    normalized = user_input.lower().strip()
    
    for keyword in ["สร้าง", "เพิ่ม", "อ่าน", "ค้นหา", "แก้ไข", "ลบ", "คัดลอก", "ผสาน", "แปลง", "สรุป", "สถิติ"]:
        if keyword in normalized:
            pattern_key = keyword
            data["patterns"][pattern_key] = data["patterns"].get(pattern_key, 0) + 1
    
    save_context(data)

def get_user_preferences():
    data = load_context()
    return data.get("user_preferences", {})

def update_preference(key, value):
    data = load_context()
    data["user_preferences"][key] = value
    save_context(data)

def get_common_patterns(n=5):
    data = load_context()
    patterns = data.get("patterns", {})
    return sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:n]

def get_context_for_analysis():
    data = load_context()
    recent = data["contexts"][-10:] if data["contexts"] else []
    return recent