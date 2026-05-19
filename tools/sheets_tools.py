import sys
import io
# Force UTF-8 stdout/stderr for proper Thai character display
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import requests
import google.auth.transport.requests
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import unicodedata
import re
import os
from utils.error_handler import retry_with_backoff, log_error, safe_execute

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Support multiple spreadsheet IDs
DEFAULT_SPREADSHEET_ID = os.getenv('DEFAULT_SPREADSHEET_ID', "1fItcYVGL1a5WcvVsdleZhe5WT8VoJ6YGgPTJFMNozrw")
SPREADSHEET_REGISTRY = {}  # name -> id mapping

# Cache for credentials and data
_credentials_cache = {}
_data_cache = {}


@retry_with_backoff(max_retries=3, default_return={"error": "Connection failed after retries"})
def get_client():
    """Return valid Google API credentials, refreshing if expired."""
    global _credentials_cache
    cache_key = "default"
    creds = _credentials_cache.get(cache_key)

    # Refresh if missing or expired (or about to expire within 60 s)
    if creds is None or not creds.valid:
        if creds is None:
            creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
        auth_req = google.auth.transport.requests.Request()
        creds.refresh(auth_req)
        _credentials_cache[cache_key] = creds

    return creds

def get_spreadsheet_id(spreadsheet_name=None):
    """Get spreadsheet ID by name or default"""
    if spreadsheet_name and spreadsheet_name in SPREADSHEET_REGISTRY:
        return SPREADSHEET_REGISTRY[spreadsheet_name]
    return DEFAULT_SPREADSHEET_ID

def set_spreadsheet(name, spreadsheet_id):
    """Register a new spreadsheet by name"""
    SPREADSHEET_REGISTRY[name] = spreadsheet_id
    return {"status": "success", "message": f"Registered spreadsheet '{name}'"}


import unicodedata

def normalize(text):
    if not text:
        return ""
    text = str(text).strip()
    # Normalize Thai characters to a standard form
    text = unicodedata.normalize('NFKC', text)
    text = text.lower()
    # Remove hidden characters
    text = re.sub(r'[\u200b-\u200f\uFEFF]', '', text)
    return text


def sanitize_search_keyword(text):
    """Normalize keyword and strip common wrapper punctuation/quotes."""
    cleaned = normalize(text)
    if not cleaned:
        return ""

    # Collapse repeated quote characters and trim surrounding wrappers.
    cleaned = re.sub(r"[\"'`’‘“”]+", "", cleaned).strip()
    cleaned = cleaned.strip("()[]{}<>.,;:!?")
    return cleaned

@retry_with_backoff(max_retries=3, default_return=[])
def get_sheet_data(sheet_name="รวม", spreadsheet_name=None):
    """Get sheet data with automatic range detection and caching"""
    import time
    
    spreadsheet_id = get_spreadsheet_id(spreadsheet_name)
    cache_key = f"{spreadsheet_id}:{sheet_name}"
    
    current_time = time.time()
    if cache_key not in _data_cache:
        _data_cache[cache_key] = {"data": None, "timestamp": 0, "ttl": 30}
    
    if _data_cache[cache_key]["data"] is not None and (current_time - _data_cache[cache_key]["timestamp"]) < _data_cache[cache_key]["ttl"]:
        return _data_cache[cache_key]["data"]
    
    creds = get_client()
    service = build('sheets', 'v4', credentials=creds)
    
    # First, get the sheet metadata to find the last row/column
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = sheet_metadata.get('sheets', [])
    target_sheet = next((s for s in sheets if s['properties']['title'] == sheet_name), None)
    
    if not target_sheet:
        return []
        
    grid_props = target_sheet['properties'].get('gridProperties', {})
    row_count = grid_props.get('rowCount', 1000)
    col_count = grid_props.get('columnCount', 26)
    
    # Use A1 notation for the full range
    full_range = f"{sheet_name}!A1:{chr(64 + min(col_count, 26))}{row_count}"
    
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=full_range
    ).execute()
    
    data = result.get('values', [])
    _data_cache[cache_key] = {"data": data, "timestamp": current_time, "ttl": 30}
    
    return data


def invalidate_cache(spreadsheet_name=None, range_name=None):
    """Clear the data cache - call after appending data"""
    spreadsheet_id = get_spreadsheet_id(spreadsheet_name)
    if spreadsheet_id and range_name:
        cache_key = f"{spreadsheet_id}:{range_name}"
        if cache_key in _data_cache:
            _data_cache[cache_key] = {"data": None, "timestamp": 0, "ttl": 30}
    elif spreadsheet_id:
        keys_to_remove = [k for k in _data_cache if k.startswith(spreadsheet_id)]
        for k in keys_to_remove:
            _data_cache[k] = {"data": None, "timestamp": 0, "ttl": 30}
    else:
        _data_cache.clear()

def find_header_row(data):
    for i, row in enumerate(data[:10]):
        row_text = " ".join(str(cell) for cell in row)
        if "ชื่อ" in row_text and "สกุล" in row_text:
            return i
    return 1

def search_student(command):
    import json

    keyword = sanitize_search_keyword(command.get("keyword", ""))

    if not keyword:
        return {"status": "success", "count": 0, "rows": []}

    exact_matches = []
    partial_matches = []
    keyword_no_space = keyword.replace(" ", "")

    # Also try variations for common Thai character differences
    keyword_variations = [keyword]
    # Handle common Thai character variations like ั vs ั
    if "ธีรภัทร" in keyword:
        keyword_variations.append(keyword.replace("ธีรภัทร", "ธีรภัทร์"))
    elif "ธีรภัทร์" in keyword:
        keyword_variations.append(keyword.replace("ธีรภัทร์", "ธีรภัทร"))

    data_folder = os.getenv('DATA_FOLDER', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data'))
    cache_path = os.path.join(data_folder, 'db_cache.json')
    
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                records = json.load(f)

            # Build fast lookup map for exact name matches
            name_map = {}
            for record in records:
                first = record.get("ชื่อ", "").strip()
                last = record.get("สกุล", "").strip()
                full_name = f"{first} {last}".strip()
                if full_name:
                    name_map[full_name] = record

            # Fast exact match lookup
            if keyword in name_map:
                return {"status": "success", "count": 1, "rows": [name_map[keyword]]}

            # Fallback to full search for partial matches and variations
            for record in records:
                if len(exact_matches) >= 50:
                    break
                
                # Check for stray rows (mostly empty)
                non_empty_values = [v for v in record.values() if v and str(v).strip()]
                if len(non_empty_values) < 2: # Ignore rows with only 1 field (like headers or stray text)
                    continue

                first_norm = normalize(record.get("ชื่อ", ""))
                last_norm = normalize(record.get("สกุล", ""))
                full_name_no_space = first_norm.replace(" ", "") + last_norm.replace(" ", "")

                # Check all keyword variations
                found_match = False
                for kw_var in keyword_variations:
                    kw_var_no_space = kw_var.replace(" ", "")
                    if kw_var_no_space and kw_var_no_space in full_name_no_space:
                        exact_matches.append(record)
                        found_match = True
                        break
                    else:
                        row_full_text = " ".join([normalize(str(v)) for v in record.values()])
                        if kw_var in row_full_text:
                            partial_matches.append(record)
                            found_match = True
                            break

                if found_match:
                    continue  # Skip to next record if we already found a match
                    
            if exact_matches:
                return {"status": "success", "count": len(exact_matches), "rows": exact_matches}
            return {"status": "success", "count": len(partial_matches), "rows": partial_matches}
        except Exception as e:
            print(f"Error reading cache: {e}")
            pass

    data = get_sheet_data()
    header_row = find_header_row(data)
    
    if header_row >= len(data):
        return {"status": "success", "count": 0, "rows": []}
    
    headers = data[header_row]
    rows = data[header_row + 1:]
    
    for row in rows:
        if len(exact_matches) >= 50:
            break
            
        record = {}
        row_full_text = ""
        for i, h in enumerate(headers):
            if h and i < len(row):
                val = str(row[i])
                record[h] = val
                row_full_text += normalize(val) + " "
        
        # Check for stray rows (mostly empty)
        non_empty_values = [v for v in record.values() if v and str(v).strip()]
        if len(non_empty_values) < 2:
            continue

        first = record.get("ชื่อ", "")
        last = record.get("สกุล", "")
        first_norm = normalize(first)
        last_norm = normalize(last)
        full_name_no_space = first_norm.replace(" ", "") + last_norm.replace(" ", "")
        
        if keyword_no_space and keyword_no_space in full_name_no_space:
            exact_matches.append(record)
        elif keyword in row_full_text:
            partial_matches.append(record)
    
    if exact_matches:
        return {"status": "success", "count": len(exact_matches), "rows": exact_matches}
    return {"status": "success", "count": len(partial_matches), "rows": partial_matches}

def append_student(command):
    creds = get_client()
    service = build('sheets', 'v4', credentials=creds)
    
    spreadsheet_id = get_spreadsheet_id(command.get("spreadsheet"))
    
    data = command.get("data", {})
    if isinstance(data, dict):
        values = list(data.values())
    elif isinstance(data, list):
        values = data
    else:
        values = [str(data)]
    
    body = {'values': [values]}
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range='รวม!A1',
        valueInputOption='RAW',
        body=body
    ).execute()
    
    # Invalidate cache after appending
    invalidate_cache(command.get("spreadsheet"))
    
    return {"status": "success", "message": "Added to Google Sheets"}

def update_student(command):
    """Update a student record in Google Sheets"""
    creds = get_client()
    service = build('sheets', 'v4', credentials=creds)
    
    spreadsheet_id = get_spreadsheet_id(command.get("spreadsheet"))
    row_index = command.get("row_index")
    
    if not row_index:
        return {"error": "row_index is required"}
    
    data = command.get("data", {})
    values = list(data.values())
    
    body = {'values': [values]}
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f'รวม!A{row_index}',
        valueInputOption='RAW',
        body=body
    ).execute()
    
    invalidate_cache(command.get("spreadsheet"))
    return {"status": "success", "message": "Updated Google Sheets data"}

def delete_student(command):
    """Delete a student record from Google Sheets by actually removing the row."""
    creds = get_client()
    service = build('sheets', 'v4', credentials=creds)

    spreadsheet_id = get_spreadsheet_id(command.get("spreadsheet"))
    row_index = command.get("row_index")

    if not row_index:
        return {"error": "row_index is required"}

    # Get the sheet ID (gid) for the target sheet (default: รวม)
    sheet_name = command.get("sheet_name", "รวม")
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = sheet_metadata.get("sheets", [])
    target_sheet = next(
        (s for s in sheets if s["properties"]["title"] == sheet_name), None
    )
    if not target_sheet:
        return {"error": f"Sheet '{sheet_name}' not found"}

    sheet_id = target_sheet["properties"]["sheetId"]

    # Use batchUpdate to delete the actual row (0-indexed)
    body = {
        "requests": [
            {
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": int(row_index) - 1,  # convert 1-based to 0-based
                        "endIndex": int(row_index),
                    }
                }
            }
        ]
    }
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body=body
    ).execute()

    invalidate_cache(command.get("spreadsheet"))
    return {"status": "success", "message": f"ลบแถวที่ {row_index} ออกจาก Google Sheets เรียบร้อยแล้ว"}

def read_database(command):
    """Read all data from the database with optional pagination, supports multiple spreadsheets"""
    spreadsheet_name = command.get("spreadsheet")
    data = get_sheet_data("รวม", spreadsheet_name)
    header_row = find_header_row(data)
    
    if header_row >= len(data):
        return {"status": "success", "count": 0, "rows": []}
    
    headers = data[header_row]
    rows = data[header_row + 1:]
    
    # Use natural header order from sheet (A-J), filter empty headers
    ordered_headers = [h for h in headers if h]
    
    # Create a mapping from header name to its index in the row
    header_to_index = {h: i for i, h in enumerate(headers)}
    
    records = []
    for row in rows:
        record = {h: row[header_to_index.get(h, 999)] if header_to_index.get(h, 999) < len(row) else "" for h in ordered_headers}
        if any(record.values()):
            records.append(record)
    
    # Pagination support
    page = command.get("page", 1)
    page_size = command.get("page_size", 50)
    start = (page - 1) * page_size
    end = start + page_size
    
    return {
        "status": "success",
        "count": len(records),
        "rows": records[start:end],
        "total_pages": (len(records) + page_size - 1) // page_size,
        "current_page": page,
        "has_more": end < len(records),
        "headers": ordered_headers
    }


def debug_print_sample():
    data = get_sheet_data()
    header_row = find_header_row(data)
    print("RAW HEADER:", data[header_row] if header_row < len(data) else "no header")
    for row in data[header_row + 1:header_row + 11]:
        print("RAW ROW:", row)
