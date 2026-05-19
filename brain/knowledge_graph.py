import json
import os
import time
from collections import defaultdict

KNOWLEDGE_FILE = "brain/knowledge.json"

def ensure_brain_dir():
    os.makedirs("brain", exist_ok=True)
    if not os.path.exists(KNOWLEDGE_FILE):
        with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
            json.dump({"entities": {}, "relations": [], "patterns": []}, f, ensure_ascii=False)

ensure_brain_dir()

def load_knowledge():
    with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_knowledge(data):
    with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_entity(entity_name, entity_type, properties=None):
    knowledge = load_knowledge()
    knowledge["entities"][entity_name] = {
        "type": entity_type,
        "properties": properties or {},
        "first_seen": time.time(),
        "last_accessed": time.time()
    }
    save_knowledge(knowledge)
    return knowledge["entities"][entity_name]

def add_person(name, rank=None, department=None, phone=None, position=None):
    """Add a person entity with Thai military/academic structure"""
    properties = {}
    if rank: properties["rank"] = rank
    if department: properties["department"] = department
    if phone: properties["phone"] = phone
    if position: properties["position"] = position
    return add_entity(name, "person", properties)

def add_rank(rank_name, level=None, abbreviation=None):
    """Add a rank entity (ยศ หน่วยงาน)"""
    properties = {}
    if level: properties["level"] = level
    if abbreviation: properties["abbreviation"] = abbreviation
    return add_entity(rank_name, "rank", properties)

def add_department(dept_name, type=None, location=None):
    """Add a department/unit entity (สังกัด/หน่วยงาน)"""
    properties = {}
    if type: properties["type"] = type
    if location: properties["location"] = location
    return add_entity(dept_name, "department", properties)

def add_file_entity(filename, sheets=None, size=None):
    """Add a file entity with metadata"""
    properties = {}
    if sheets: properties["sheets"] = sheets
    if size: properties["size"] = size
    return add_entity(filename, "file", properties)

def add_relation(from_entity, to_entity, relation_type, strength=1.0):
    knowledge = load_knowledge()
    existing = [r for r in knowledge["relations"] if r["from"] == from_entity and r["to"] == to_entity and r["type"] == relation_type]
    if existing:
        existing[0]["strength"] = min(existing[0]["strength"] + 0.1, 1.0)
    else:
        knowledge["relations"].append({
            "from": from_entity,
            "to": to_entity,
            "type": relation_type,
            "strength": strength,
            "timestamp": time.time()
        })
    save_knowledge(knowledge)

def get_related_entities(entity_name, relation_type=None):
    knowledge = load_knowledge()
    related = []
    for rel in knowledge["relations"]:
        if rel["from"] == entity_name:
            if relation_type is None or rel["type"] == relation_type:
                related.append((rel["to"], rel["strength"]))
    return sorted(related, key=lambda x: x[1], reverse=True)

def infer_knowledge(entity_name):
    knowledge = load_knowledge()
    entity = knowledge["entities"].get(entity_name)
    if not entity:
        return None
    
    inferred = {
        "entity": entity,
        "related": get_related_entities(entity_name)
    }
    return inferred

def update_entity_access(entity_name):
    knowledge = load_knowledge()
    if entity_name in knowledge["entities"]:
        knowledge["entities"][entity_name]["last_accessed"] = time.time()
        save_knowledge(knowledge)

def find_connection(from_entity, to_entity, max_depth=3):
    """Find connection path between two entities using proper BFS with visited tracking."""
    knowledge = load_knowledge()
    relations = knowledge.get("relations", [])

    # Build adjacency list for fast lookup
    adjacency = {}
    for rel in relations:
        src = rel["from"]
        if src not in adjacency:
            adjacency[src] = []
        adjacency[src].append(rel["to"])

    # BFS
    from collections import deque
    queue = deque()
    queue.append((from_entity, [from_entity]))
    visited = {from_entity}

    while queue:
        current, path = queue.popleft()
        if len(path) - 1 >= max_depth:
            continue
        for neighbor in adjacency.get(current, []):
            if neighbor == to_entity:
                return path + [neighbor]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor]))

    return None

def get_common_patterns():
    knowledge = load_knowledge()
    entity_types = defaultdict(int)
    for entity in knowledge["entities"].values():
        entity_types[entity["type"]] += 1
    return dict(sorted(entity_types.items(), key=lambda x: x[1], reverse=True))

def get_entities_by_type(entity_type):
    """Get all entities of a specific type"""
    knowledge = load_knowledge()
    result = []
    for name, entity in knowledge["entities"].items():
        if entity["type"] == entity_type:
            result.append({
                "name": name,
                "properties": entity["properties"],
                "last_accessed": entity["last_accessed"]
            })
    return sorted(result, key=lambda x: x["last_accessed"], reverse=True)

def get_entity_suggestions(partial_name, entity_type=None):
    """Get entity suggestions based on partial name match"""
    knowledge = load_knowledge()
    import difflib
    suggestions = []
    
    for name, entity in knowledge["entities"].items():
        if entity_type and entity["type"] != entity_type:
            continue
        if partial_name.lower() in name.lower():
            suggestions.append({
                "name": name,
                "type": entity["type"],
                "properties": entity["properties"]
            })
    
    # Fuzzy match
    if not suggestions:
        matches = difflib.get_close_matches(partial_name, 
            [n for n, e in knowledge["entities"].items() 
             if not entity_type or e["type"] == entity_type], 
            n=5, cutoff=0.4)
        for match in matches:
            entity = knowledge["entities"][match]
            suggestions.append({
                "name": match,
                "type": entity["type"],
                "properties": entity["properties"]
            })
    
    return suggestions