import re
import difflib


def fuzzy_match(text, choices, threshold=0.6):
    """Find closest match using fuzzy string matching."""
    matches = difflib.get_close_matches(text, choices, n=1, cutoff=threshold)
    return matches[0] if matches else None


def extract_number(text):
    """Extract numbers from text."""
    numbers = re.findall(r'\d+', text)
    return [int(n) for n in numbers]


def normalize_thai(text):
    """Normalize Thai text by removing tone marks and common variations."""
    import unicodedata
    text = unicodedata.normalize("NFKD", text)
    replacements = {
        "่": "", "้": "", "๊": "", "็": "",
        "ิ": "ิ", "ี": "ี", "ึ": "ึ", "ื": "ื", "็": "",
        "์": "", "ํ": "", "๎": ""
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.strip().lower()


def match_name(name, candidates):
    """Match a name against a list of candidates."""
    name_norm = normalize_thai(name)
    for candidate in candidates:
        cand_norm = normalize_thai(candidate)
        if name_norm == cand_norm:
            return candidate
        if name_norm in cand_norm or cand_norm in name_norm:
            return candidate
    return None