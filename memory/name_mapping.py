import json
import os
import time
from typing import List, Set, Tuple, Optional
from tools.sheets_tools import read_database, normalize

# Cache for student names to avoid frequent database queries
_student_names_cache: Optional[List[str]] = None
_cache_timestamp: float = 0
CACHE_TTL = 300  # 5 minutes in seconds

# File to store learned mappings from misspelled names to correct names
MAPPINGS_FILE = "memory/name_mappings.json"

def _ensure_memory_dir():
    os.makedirs("memory", exist_ok=True)

def _load_mappings() -> dict:
    _ensure_memory_dir()
    if not os.path.exists(MAPPINGS_FILE):
        return {}
    try:
        with open(MAPPINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def _save_mappings(mappings: dict):
    _ensure_memory_dir()
    with open(MAPPINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(mappings, f, ensure_ascii=False, indent=2)

def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute the Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    # Now len(s1) >= len(s2)
    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def similarity(s1: str, s2: str) -> float:
    """Return a similarity score between 0 and 1 using Levenshtein distance.
    The similarity is defined as max(0, 1 - (distance / len(s1))), where s1 is the first string.
    If s1 is empty, return 0.0 (unless s2 is also empty, then 1.0).
    """
    if len(s1) == 0 and len(s2) == 0:
        return 1.0
    if len(s1) == 0:
        return 0.0
    dist = levenshtein_distance(s1, s2)
    # Avoid negative similarity
    return max(0.0, 1.0 - (dist / len(s1)))

def get_all_student_names(force_refresh: bool = False) -> List[str]:
    """Get a list of all possible student name representations from the database.
    Returns a list of strings that represent a student's name in various formats.
    """
    global _student_names_cache, _cache_timestamp
    now = time.time()
    if _student_names_cache is not None and (now - _cache_timestamp) < CACHE_TTL and not force_refresh:
        return _student_names_cache

    try:
        # Get all data from the database cache instead of live database
        import json
        import os
        data_folder = os.getenv('DATA_FOLDER', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data'))
        cache_path = os.path.join(data_folder, 'db_cache.json')

        if not os.path.exists(cache_path):
            _student_names_cache = []
            _cache_timestamp = now
            return _student_names_cache

        with open(cache_path, 'r', encoding='utf-8') as f:
            records = json.load(f)

        names_set: Set[str] = set()
        for record in records:
            # Skip records with mostly empty fields
            non_empty_values = [v for v in record.values() if v and str(v).strip()]
            if len(non_empty_values) < 2:
                continue

            title = record.get("ยศ", "").strip()
            first_name = record.get("ชื่อ", "").strip()
            last_name = record.get("สกุล", "").strip()

            # Construct various representations
            full_with_title = f"{title} {first_name} {last_name}".strip()
            full_without_title = f"{first_name} {last_name}".strip()

            if full_with_title and len(full_with_title.split()) >= 2:
                names_set.add(full_with_title)
            if full_without_title and len(full_without_title.split()) >= 2:
                names_set.add(full_without_title)

        _student_names_cache = list(names_set)
        _cache_timestamp = now
        return _student_names_cache
    except Exception as e:
        # In case of any error, return empty list and log
        print(f"Error fetching student names for cache: {e}")
        _student_names_cache = []
        _cache_timestamp = now
        return _student_names_cache

def get_corrected_keyword(keyword: str) -> Tuple[str, str, List[str]]:
    """Return a corrected keyword, correction type, and suggestions.

    Correction type:
        "exact"  -> found in learned mapping (exact match after normalisation)
        "high"   -> similarity >= 0.92 AND keyword is long enough (>= 4 chars)
                    to avoid false corrections on short words
        "low"    -> similarity in [0.80, 0.92) -> return original + suggestions
        "none"   -> similarity < 0.80 -> return original, no suggestions
    """
    normalized_keyword = normalize(keyword)
    mappings = _load_mappings()
    if normalized_keyword in mappings:
        return mappings[normalized_keyword], "exact", []

    try:
        student_names = get_all_student_names()
    except Exception as e:
        print(f"Error getting student names: {e}")
        return keyword, "none", []
    if not student_names:
        return keyword, "none", []

    # Compute similarities
    scored_names = []
    for name in student_names:
        sim = similarity(normalized_keyword, normalize(name))
        scored_names.append((sim, name))
    scored_names.sort(key=lambda x: x[0], reverse=True)

    best_sim, best_name = scored_names[0]
    second_sim, second_name = scored_names[1] if len(scored_names) > 1 else (0.0, "")

    suggestions: List[str] = []
    if best_name and best_name != keyword:
        suggestions.append(best_name)
    if second_name and second_name != keyword and second_name not in suggestions:
        suggestions.append(second_name)

    # Require keyword to be at least 4 chars before auto-correcting to avoid
    # short-keyword false positives (e.g. "หา" → wrong name)
    min_len_for_autocorrect = 4

    if best_sim >= 0.92 and len(normalized_keyword) >= min_len_for_autocorrect:
        # High confidence: learn and return corrected name
        mappings[normalized_keyword] = best_name
        _save_mappings(mappings)
        return best_name, "high", []
    elif best_sim >= 0.80:
        # Medium confidence: return original + suggestions for user to choose
        return keyword, "low", suggestions[:2]
    else:
        return keyword, "none", []

def learn_mapping(misspelled: str, correct: str):
    """Learn a new mapping from a misspelled name to the correct name."""
    normalized_misspelled = normalize(misspelled)
    mappings = _load_mappings()
    mappings[normalized_misspelled] = correct
    _save_mappings(mappings)