#agent.py
import fractions
import fractions
from tools.desktop_tools import open_excel, open_excel_file, append_row_live
import win32com.client
import json
import re
import requests
import subprocess
import time
from tools.desktop_tools import open_excel, open_excel_file
import os
import threading
from typing import Any, Dict, List, cast
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
    save_uploaded_file,
    learn_from_file_content,
    export_to_csv,
    export_to_html,
    export_dashboard,
    ensure_file_path,
    validate_excel_data,
    ensure_file_path,
)
from tools.sheets_tools import search_student, append_student, read_database, update_student, delete_student
from memory.memory_manager import add_skill, get_skill, list_skills, load_skills
from memory.name_mapping import get_corrected_keyword, learn_mapping
from brain.ai_brain import brain
from utils.logger import push_log

from dotenv import load_dotenv

load_dotenv()

DATA_FOLDER = os.getenv('DATA_FOLDER', os.path.join(os.path.dirname(__file__), 'data'))
OLLAMA_URL = os.getenv('OLLAMA_URL', "http://localhost:11434/api/generate")
MODEL_NAME = os.getenv('OLLAMA_MODEL', "qwen3")

LAST_USED_FILE = "students.xlsx"
# Thread-safe storage for last search results
_search_results_lock = threading.Lock()
LAST_SEARCH_RESULTS: List[Dict] = []  # Neural memory for search results


def ensure_ollama_running():
    try:
        response = requests.get("http://localhost:11434", timeout=5)
        return response.status_code == 200
    except Exception:
        try:
            subprocess.Popen(["ollama",
    "serve"],
    stdout=subprocess.DEVNULL,
     stderr=subprocess.DEVNULL)
            time.sleep(5)  # Increase wait time
            response = requests.get("http://localhost:11434", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"Could not start Ollama: {e}")
            return False


def ask_ollama(prompt: str):
    if not ensure_ollama_running():
        return "{}"
    payload = {
    "model": MODEL_NAME,
    "prompt": prompt,
    "stream": False,
     "keep_alive": "5m"}
    try:
        # Increase timeout and add retries
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        return response.json().get("response", "{}")
    except requests.exceptions.Timeout:
        print("Ollama request timed out")
        return "{}"
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return "{}"


SYSTEM_PROMPT = """
You are J.A.R.V.I.S, an advanced Excel and Student Database agent.
Convert Thai user commands into JSON.

Capabilities:
- Manage local Excel files (create_excel_file, read_excel_file, append_row, update_row, delete_row, copy_data, merge_files, summarize_data, get_statistics, analyze_file).
- Manage Google Sheets database (search_student, append_student, read_database, sync_db).
- Proactive Analysis: If asked to summarize or analyze, provide deep insights.
- Multi-step Logic: If the user asks for multiple things, return an ARRAY of action objects.

Definitions:
- "database", "db", "ฐานข้อมูล": Google Sheets actions.
- "file", "excel", "ไฟล์", ".xlsx": Local Excel actions.

Rules:
1. Return ONLY valid JSON.
2. If multiple actions are needed, return: [{"action": "..."}, {"action": "..."}]
3. Extract all relevant entities (names, ranks, filenames).
4. For 'analyze_file', provide structural and data pattern insights.
5. IF the user mentions "ไฟล์" or ".xls", use Excel actions (e.g., "append_row"). DO NOT use Google Sheets actions.
6. IF the user mentions "ฐานข้อมูล" (database) or "db", use Google Sheets actions (e.g., "append_student").
"""


def format_student_result(result):
    if result.get("count", 0) == 0:
        return "ไม่พบข้อมูล"
    rows = result.get("rows", [])
    if not rows:
        return "ไม่พบข้อมูล"
    lines = []
    for r in rows:
        rank, name, last = r.get(
            "ยศ", "-"), r.get("ชื่อ", "-"), r.get("สกุล", "-")
        pos, unit, phone = r.get(
            "ตำแหน่ง", "-"), r.get("สังกัด", "-"), r.get("เบอร์โทรศัพท์", "-")
        lines.append(
            f"{rank}\t{name}\t{last}\t{pos}\tสังกัด: {unit}\tเบอร์: {phone}")
    return "\n".join(lines)


def extract_keyword(text):
    if not text: return ""
    original = text.strip()
    text = original
    
    # 1. Remove prefixes from start
    prefixes = ['หาข้อมูล', 'ดูข้อมูล', 'ค้นหา', 'หาเบอร์ของ', 'หาเบอร์', 'หา', 'ช่วยหา', 'ขอข้อมูล', 'ข้อมูล', 'นำข้อมูล']
    for p in sorted(prefixes, key=len, reverse=True):
        if text.startswith(p):
            text = text[len(p):].strip()
            break
            
    # 2. Remove suffixes from end (iteratively)
    suffixes = ['จาก db', 'ใน db', 'จากฐานข้อมูล', 'ในฐานข้อมูล', 'ทำไมไม่มี', 'ทำไมหาไม่เจอ', 'อยู่ไหน', 'ครับ', 'ค่ะ', 'ครับผม', 'นะ', 'หน่อย', 'มั้ย', 'สิ', 'ให้หน่อย', 'ดูหน่อย', 'ไปใส่ในไฟล์', 'ลงในไฟล์', 'ลงไฟล์']
    suffixes = sorted(suffixes, key=len, reverse=True)
    
    changed = True
    while changed:
        changed = False
        for s in suffixes:
            if text.endswith(s):
                text = text[:-len(s)].strip()
                changed = True
                
    # 3. If everything was stripped, return original (minus obvious prefixes)
    extracted = text if text else original.replace('หาข้อมูล', '').replace('จาก db', '').strip()
    # Remove common quote wrappers from user input like 'สุวรรณศรี' or "สุวรรณศรี"
    extracted = re.sub(r"[\"'`’‘“”]+", "", extracted).strip()
    return extracted


def extract_filename(text):
    # First, look for any .xlsx or .xls or .xlxs filename anywhere
    fx_match = re.search(r'([a-zA-Z0-9_\-\u0E00-\u0E7F]+\.xl[s|x][x|s]?)', text, re.IGNORECASE)
    if fx_match:
        name = fx_match.group(1)
        if not name.endswith('.xlsx'):
            name = name.rsplit('.', 1)[0] + '.xlsx'
        return name

    # Priority 0: after "ในไฟล์", "ลงไฟล์", "ใส่ใน", "เซฟลง"
    target_match = re.search(r'(?:ในไฟล์|ลงในไฟล์|ลงไฟล์|ใส่ใน|เซฟลง|ใส่ไฟล์)\s*([\u0E00-\u0E7F0-9a-zA-Z._-]+)', text)
    if target_match:
        name = target_match.group(1).strip()
    else:
        # Priority 1: after "ชื่อไฟล์" or "ชื่อ"
        match = re.search(r'(?:ชื่อไฟล์|ชื่อ)\s*([\u0E00-\u0E7F0-9a-zA-Z._-]+?)\s*(?:โดย|คือ|และ|$)', text)
        if match:
            name = match.group(1).strip()
        else:
            # Priority 2: after "สร้างไฟล์" or "สร้างไฟล์ใหม่"
            match = re.search(r'สร้างไฟล์(?:ใหม่)?\s+([\u0E00-\u0E7F0-9a-zA-Z._-]+?)\s*(?:โดย|คือ|และ|$)', text)
            if match:
                name = match.group(1).strip()
            else:
                # Fallback: trailing number or default
                num_match = re.search(r'(\d+)$', text.strip())
                name = num_match.group(1) if num_match else "new_file"
    
    if not name or name.lower() == "excel" or name == "ข้อมูล":
        name = "new_file"
    if not name.endswith('.xlsx'):
        name += '.xlsx'
    return name



def resolve_target_excel_from_command(text):
    """
    Detect a local Excel destination from phrases like:
    'เพิ่มใน students', 'นำไปเพิ่มใน students', 'ลงไฟล์ roster.xlsx', 'ใส่ใน students.xlsx'.
    Returns normalized '*.xlsx' or None if not clearly an Excel target.
    """
    if not text:
        return None
    low = text.lower()
    if any(w in low for w in ["ฐานข้อมูล", "database", "sync db", "google sheet", "google sheets"]):
        return None

    # Priority 1: explicit .xlsx filename anywhere in text
    fx_match = re.search(r"([\w\u0E00-\u0E7F.-]+\.xlsx?)", text, re.IGNORECASE)
    if fx_match:
        name = fx_match.group(1).strip()
        if not name.endswith(".xlsx"):
            name = name.rsplit(".", 1)[0] + ".xlsx"
        return name

    # Priority 2: broad pattern — any verb + ใน/ลง/เข้า + optional ไฟล์ + filename
    # Covers: เพิ่มใน X, นำไปเพิ่มใน X, ใส่ใน X, บันทึกลง X, นำลงใน X, เพิ่มลงใน X
    m = re.search(
        r"(?:เพิ่ม|ใส่|บันทึก|ลง|นำ(?:ไป)?(?:เพิ่ม)?(?:ข้อมูล)?)"
        r"(?:ข้อมูล)?"
        r"(?:ลง|ใน|เข้า)+"
        r"(?:ไฟล์)?\s*"
        r"([\u0E00-\u0E7Fa-zA-Z0-9._-]+)",
        text,
    )
    if not m:
        return None
    base = m.group(1).strip()
    if base.lower() in ("db", "database", "sheet", "sheets"):
        return None
    if not base.endswith(".xlsx"):
        base = base + ".xlsx"
    return base


def extract_student_data(text):
    data = {
        "ลำดับ": "",
        "ยศ": "",
        "ชื่อ": "",
        "สกุล": "",
        "ตำแหน่ง": "",
        "สังกัด": "",
        "เบอร์โทรศัพท์": "",
    }
    # Full rank list aligned with THAI_RANKS in ai_brain.py
    ranks = [
        "พลเอก", "พลโท", "พลตรี", "พล.", "พลโท.",
        "นพ.", "น.พ.", "พ.อ.", "พ.ท.", "พ.ต.",
        "ร.อ.", "ร.ท.", "ร.ต.",
        "จ่อ.", "ส.ท.", "ส.ต.", "ส.จ.",
        "โทร.", "พัน.", "พัน.๑", "พัน.๒",
        "ร้อย.", "ร้อย.๑", "ร้อย.๒",
        "นนร.",
    ]
    # Sort longest first to avoid partial matches (e.g. "พ.ต." before "พ.")
    ranks_sorted = sorted(ranks, key=len, reverse=True)

    # Extract rank first
    for r in ranks_sorted:
        if r in text:
            data["ยศ"] = r
            text = text.replace(r, ' ', 1)
            break
    
    # Extract sequence (ลำดับ) - ยอด xxx
    seq_match = re.search(r'ยอด\s*(\d+)', text)
    if seq_match:
        data["ลำดับ"] = seq_match.group(1)
        text = text.replace(seq_match.group(0), ' ')
    
    # Extract position like พัน.3, ร้อย.2
    pos_match = re.search(r'(พัน\.\s*\d+|ร้อย\.\s*\d+|พัน\s*\d+|ร้อย\s*\d+)', text)
    if pos_match:
        data["ตำแหน่ง"] = pos_match.group(1).replace(' ', '')
        text = text.replace(pos_match.group(0), ' ')
    
    # Remove unwanted words
    text = text.replace('เพิ่ม', '').replace('นักเรียน', '').replace('ลงในตาราง', '').replace('ลงในไฟล์', '').replace('ในฐานข้อมูล', '').replace('ใน db', '').replace('ในฐาน', '').replace('มี', '').strip()
    
    # Extract name using "ชื่อ" keyword
    name_match = re.search(r'ชื่อ\s+(\S+)\s+สกุล\s+(\S+)', text)
    if name_match:
        data["ชื่อ"] = name_match.group(1)
        data["สกุล"] = name_match.group(2)
    else:
        # Try another pattern: ชื่อ X Y สกุล Z
        name_match2 = re.search(r'ชื่อ\s+(\S+(?:\s+\S+)*?)\s+สกุล\s+(\S+)', text)
        if name_match2:
            data["ชื่อ"] = name_match2.group(1).strip()
            data["สกุล"] = name_match2.group(2)
        else:
            # Just get words after "ชื่อ"
            after_name = re.search(r'ชื่อ\s+(.+?)(?:\s+สกุล|$)', text)
            if after_name:
                name_parts = after_name.group(1).strip().split()
                if len(name_parts) >= 2:
                    data["ชื่อ"] = name_parts[0]
                    data["สกุล"] = name_parts[1]
                elif len(name_parts) == 1:
                    data["ชื่อ"] = name_parts[0]

    return data


def process_command(user_command: str):
    push_log("[System] วิเคราะห์คำสั่ง...")
    # 1. Natural Conversation Layer
    chat_category = brain.is_small_talk(user_command)
    if chat_category:
        return {
            "status": "success",
            "message": brain.get_conversation_response(chat_category),
            "type": "conversation"
        }

    global LAST_USED_FILE
    global LAST_SEARCH_RESULTS
    cmd_lower = user_command.lower()
    is_db_context = any(word in cmd_lower for word in ["database", "db", "ฐานข้อมูล"])

    # 1.5 PROACTIVE DETECTION (Skip slow LLM for obvious tasks)
    command = None
    
    # Context-aware Save detection
    if any(word in user_command for word in ["นำข้อมูล", "บันทึกข้อมูล", "เอาข้อมูล", "เซฟข้อมูล"]) and any(word in user_command for word in ["ใส่ในไฟล์", "ลงในไฟล์", "ไปใส่", "เซฟลง"]):
        filename = extract_filename(user_command)
        if filename == "new_file.xlsx": filename = LAST_USED_FILE
        
        if LAST_SEARCH_RESULTS:
            actions = []
            for row in LAST_SEARCH_RESULTS:
                actions.append({"action": "append_row", "file": filename, "data": row})
            
            # Reset memory after saving to prevent duplicate saves
            LAST_SEARCH_RESULTS = []
            command = actions
        else:
             return {"status": "error", "message": "ไม่พบข้อมูลที่เคยค้นหาก่อนหน้าในความจำ Neural (ลองหาข้อมูลก่อนครับ)"}

    # Append last DB search results into a named Excel file (e.g. "เพิ่มใน students", "นำไปเพิ่มใน students")
    elif LAST_SEARCH_RESULTS and not is_db_context:
        excel_dest = resolve_target_excel_from_command(user_command)
        verb_ok = any(w in user_command for w in [
            "เพิ่ม", "ใส่", "บันทึก", "ลง", "นำ", "ไป", "เอา", "copy", "คัดลอก"
        ])
        if excel_dest and verb_ok:
            push_log(f"[Intent] detect append previous search result → {excel_dest}")
            actions = [
                {"action": "append_row", "file": excel_dest, "data": dict(row)}
                for row in LAST_SEARCH_RESULTS
            ]
            LAST_SEARCH_RESULTS = []
            command = actions
        elif verb_ok and not excel_dest:
            # ไม่ระบุชื่อไฟล์ → ใช้ไฟล์ล่าสุด
            push_log(f"[Intent] detect append → ใช้ไฟล์ล่าสุด: {LAST_USED_FILE}")
            actions = [
                {"action": "append_row", "file": LAST_USED_FILE, "data": dict(row)}
                for row in LAST_SEARCH_RESULTS
            ]
            LAST_SEARCH_RESULTS = []
            command = actions

    # Sync DB detection
    elif "โหลด db" in cmd_lower or "โหลดฐานข้อมูล" in user_command or "sync db" in cmd_lower:
        command = {"action": "sync_db"}
    
    # Search detection
    elif any(word in user_command for word in ["หาข้อมูล", "ค้นหา", "หาเบอร์", "ดูข้อมูล"]):
        raw_keyword = extract_keyword(user_command)
        if raw_keyword and len(raw_keyword) > 1:
            # Normalize to handle typos like 'เเละ' (double sara-e) -> 'และ' (sara-ae)
            from tools.sheets_tools import normalize
            norm_keyword = normalize(raw_keyword)
            
            # Split by connectors: และ, กับ, ,, &
            keywords = re.split(r'\s*(?:และ|กับ|,|&)\s*', norm_keyword)
            if len(keywords) > 1:
                command = []
                for kw in keywords:
                    kw = kw.strip()
                    if len(kw) > 1:
                        # Apply keyword correction for each keyword
                        corrected_kw, correction_type, suggestions = get_corrected_keyword(kw)
                        action_type = "search_student" if is_db_context or "ไฟล์" not in user_command else "search_excel"
                        cmd_obj = {"action": action_type, "keyword": corrected_kw}
                        if action_type == "search_excel": cmd_obj["file"] = LAST_USED_FILE
                        command.append(cmd_obj)
                        # Store correction info for steps? We'll handle in execute_single_command or add to steps later
            else:
                # Single keyword
                keyword = keywords[0].strip() if keywords else ""
                if keyword:
                    # Apply keyword correction
                    corrected_keyword, correction_type, suggestions = get_corrected_keyword(keyword)
                    action_type = "search_student" if is_db_context or "ไฟล์" not in user_command else "search_excel"
                    command = {"action": action_type, "keyword": corrected_keyword}
                    if action_type == "search_excel": command["file"] = LAST_USED_FILE
                    # We could store the original keyword and correction info here for steps,
                    # but execute_single_command will add steps based on correction_type
        else:
            command = None
    elif "เปิด excel" in cmd_lower:
        command = {"action": "open_excel"}

    elif "เปิดไฟล์" in user_command and ".xlsx" in user_command:
        filename = extract_filename(user_command)
        command = {
            "action": "open_excel_file",
            "file": filename
    }
    # 2. LLM Layer (For complex tasks)
    if not command:
        prev_last_used = LAST_USED_FILE
        push_log("[Brain] ส่งคำสั่งไปยัง LLM (Ollama)...")
        full_prompt = SYSTEM_PROMPT + "\nUser: " + user_command
        raw = ask_ollama(full_prompt)
        push_log("[Brain] LLM ประมวลผลเสร็จสิ้น")

        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        try:
            command = json.loads(raw)
            if not isinstance(command, (dict, list)):
                command = None
        except (json.JSONDecodeError, KeyError):
            command = None

    if not command:
        return {"status": "error", "message": "ไม่สามารถตีความคำสั่งได้ กรุณาลองใหม่อีกครั้ง"}

    if isinstance(command, list) and len(command) > 0 and not any(isinstance(c, dict) for c in command):
        # Handle case where LLM might return a list of strings or something weird
        command = None

    if not command:
         return {"status": "error", "message": "ไม่สามารถตีความคำสั่งได้ กรุณาลองใหม่อีกครั้ง"}

    # Intercept and correct LLM mistakes regarding Excel vs Google Sheets
    if isinstance(command, dict) and command.get("action") == "append_student":
        excel_dest = resolve_target_excel_from_command(user_command)
        if LAST_SEARCH_RESULTS and excel_dest and not is_db_context:
            command = [
                {"action": "append_row", "file": excel_dest, "data": dict(r)}
                for r in LAST_SEARCH_RESULTS
            ]
            LAST_SEARCH_RESULTS = []
        elif not is_db_context and ("ไฟล์" in user_command or ".xls" in user_command):
            command["action"] = "append_row"
            extracted_file = extract_filename(user_command)
            command["file"] = extracted_file if extracted_file != "new_file.xlsx" else LAST_USED_FILE

    # Robust Search Fallback — only runs when no command has been determined yet
    if not command:
        if any(word in user_command for word in ["หาข้อมูล", "ค้นหา", "หาเบอร์", "ดูข้อมูล"]):
            keyword = extract_keyword(user_command)
            if keyword and len(keyword) > 1:
                if is_db_context:
                    command = {"action": "search_student", "keyword": keyword}
                elif "ไฟล์" in user_command or ".xls" in user_command:
                    command = {"action": "search_excel", "keyword": keyword, "file": LAST_USED_FILE}
                else:
                    command = {"action": "search_student", "keyword": keyword}

    def get_full_data(text):
        extracted = extract_student_data(text)
        search_parts = [extracted.get("ยศ", ""), extracted.get("ชื่อ", ""), extracted.get("สกุล", "")]
        search_key = " ".join(p for p in search_parts if p).strip()
        if not search_key:
            return extracted
        try:
            db_result = search_student({"keyword": search_key})
            if db_result.get("count", 0) > 0:
                return db_result["rows"][0]
        except Exception:
            pass
        return extracted

    # Fallback for creating file
    if "สร้างไฟล์" in user_command or "สร้างไฟล์ใหม่" in user_command:
        if not command:
            filename = extract_filename(user_command)
            # Check if there's student data in command
            if any(kw in user_command for kw in ["นักเรียน", "เพิ่ม", "ชื่อ"]) and "ชื่อ" in user_command:
                extracted = extract_student_data(user_command)
                command = {"action": "create_excel_file", "file": filename, "data": extracted}
            else:
                command = {"action": "create_excel_file", "file": filename}

    # Fallback for listing files
    if "ดูไฟล์" in user_command or "ไฟล์ทั้งหมด" in user_command or "รายชื่อไฟล์" in user_command or "แสดงไฟล์" in user_command:
        if not command:
            command = {"action": "list_files"}

    # Fallback for reading database
    if "อ่านฐานข้อมูล" in user_command or "ดูฐานข้อมูล" in user_command:
        # Ensure command is a dict before inspecting/setting keys
        if not isinstance(command, dict) or command.get("action") != "read_database":
            cmd_dict: Dict[str, Any] = {"action": "read_database"}
            page_match = re.search(r'หน้า\s*(\d+)', user_command)
            if page_match:
                # set on local dict first
                cmd_dict["page"] = int(page_match.group(1))
            command = cmd_dict

    # Fallback for syncing database
    if "โหลด db" in user_command.lower() or "โหลดฐานข้อมูล" in user_command or "sync db" in user_command.lower():
        command = {"action": "sync_db"}

    # Fallback for adding data
    if ("เพิ่ม" in user_command or "放入" in user_command) and not command:
        full_data = get_full_data(user_command)
        if is_db_context:
            command = {"action": "append_student", "data": full_data}
        elif "ไฟล์" in user_command or ".xlsx" in user_command:
            extracted_file = extract_filename(user_command)
            filename = extracted_file if extracted_file != "new_file.xlsx" else LAST_USED_FILE
            command = {"action": "append_row", "file": filename, "data": full_data}

    # Fallback for copying data
    if "คัดลอก" in user_command or "copy" in user_command.lower():
        if not command:
            src_file = extract_filename(user_command) or LAST_USED_FILE
            dest_match = re.search(r'(?:ไปยัง|เป็น|to)\s*([a-zA-Z0-9._-]+)', user_command)
            dest_file = dest_match.group(1) + ".xlsx" if dest_match else "copy.xlsx"
            command = {"action": "copy_data", "file": src_file, "dest_file": dest_file}

    # Fallback for merging files
    if "ผสาน" in user_command or "รวม" in user_command or "merge" in user_command.lower():
        if not command:
            main_file = extract_filename(user_command) or LAST_USED_FILE
            merge_match = re.search(r'(?:กับ|และ|with)\s*([a-zA-Z0-9._-]+)', user_command)
            merge_file = merge_match.group(1) + ".xlsx" if merge_match else "students.xlsx"
            command = {"action": "merge_files", "file": main_file, "merge_file": merge_file}

    # Fallback for converting format
    if "แปลง" in user_command or "convert" in user_command.lower():
        if not command:
            filename = extract_filename(user_command) or LAST_USED_FILE
            fmt = "csv"
            if "json" in user_command.lower():
                fmt = "json"
            command = {"action": "convert_format", "file": filename, "format": fmt}

    # Fallback for summarizing data
    if "สรุป" in user_command or "summarize" in user_command.lower():
        if not command:
            filename = extract_filename(user_command) or LAST_USED_FILE
            command = {"action": "summarize_data", "file": filename}

    # Fallback for getting statistics
    if "สถิติ" in user_command or "statistic" in user_command.lower():
        if not command:
            filename = extract_filename(user_command) or LAST_USED_FILE
            command = {"action": "get_statistics", "file": filename}

    # Fallback for data validation
    if "ตรวจสอบ" in user_command or "validate" in user_command.lower():
        if not command:
            filename = extract_filename(user_command) or LAST_USED_FILE
            command = {"action": "validate_data", "file": filename}

    # Fallback for dashboard
    if "แดชบอร์ด" in user_command or "dashboard" in user_command.lower():
        if not command:
            filename = extract_filename(user_command) or LAST_USED_FILE
            command = {"action": "dashboard", "file": filename}

    # Fallback for export CSV
    if "ส่งออก csv" in user_command or "export csv" in user_command.lower():
        if not command:
            filename = extract_filename(user_command) or LAST_USED_FILE
            command = {"action": "export_csv", "file": filename}

    # Fallback for export HTML
    if "ส่งออก html" in user_command or "export html" in user_command.lower():
        if not command:
            filename = extract_filename(user_command) or LAST_USED_FILE
            command = {"action": "export_html", "file": filename}

    if isinstance(command, list):
        results = []
        push_log(f"[System] multi-command: {len(command)} คำสั่ง")
        for i, cmd in enumerate(command, 1):
            push_log(f"[System] ดำเนินการคำสั่ง {i}/{len(command)}: {cmd.get('action', '?')}")
            res = execute_single_command(cmd, user_command)
            results.append(res)
        
        # Combine messages and steps
        combined_message = " | ".join([r.get("message", "") for r in results if r.get("message")])
        combined_steps = []
        combined_rows = []
        for r in results:
            combined_steps.extend(r.get("steps", []))
            if r.get("rows"):
                combined_rows.extend(r.get("rows"))
            
        final_result = {
            "status": "success",
            "message": combined_message,
            "steps": combined_steps,
            "rows": combined_rows,
            "count": len(combined_rows),
            "multi_results": results
        }
        return final_result
    
    return execute_single_command(command, user_command)


def execute_single_command(command, user_command):
    global LAST_USED_FILE
    prev_last_used = LAST_USED_FILE
    
    if not command or not isinstance(command, dict) or not command.get("action"):
        if any(word in user_command for word in ["ค้น", "หา", "เบอร์"]):
            keyword = extract_keyword(user_command)
            if keyword:
                is_db_context = any(word in user_command.lower() for word in ["database", "db", "ฐานข้อมูล"])
                if is_db_context or "ในไฟล์" not in user_command:
                    steps = [f"ค้นหาฐานข้อมูล: {keyword}"]
                    data = search_student({"keyword": keyword})
                    steps.append(f"พบ: {data.get('count', 0)} รายการ")
                    return {
                        "status": "success",
                        "message": f"ค้นหาในฐานข้อมูลพบ {data.get('count', 0)} รายการ",
                        "rows": data.get("rows", []),
                        "formatted": format_student_result(data),
                        "filename": "Google Sheets Database",
                        "steps": steps
                    }
                else:
                    steps = [f"ค้นหาในไฟล์: {LAST_USED_FILE}", f"คำค้นหา: {keyword}"]
                    result = search_excel({"file": LAST_USED_FILE, "keyword": keyword})
                    if isinstance(result, dict):
                        r = cast(Dict[str, Any], result)
                        r["filename"] = LAST_USED_FILE
                        r["steps"] = steps
                        return r
                    else:
                        # Normalize non-dict result into dict
                        return {
                            "status": "success",
                            "rows": result if isinstance(result, list) else [],
                            "filename": LAST_USED_FILE,
                            "steps": steps
                        }
        return brain.handle_unrecognized_command(user_command)

    if "file" in command:
        from tools.excel_tools import ensure_file_path as check_file
        file_check = check_file(command["file"])
        if command.get("action") != "create_excel_file" and not file_check["exists"] and file_check["suggestion"]:
            return {
                "status": "confirm",
                "message": f"ไม่พบไฟล์ '{command['file']}' คุณหมายถึงไฟล์ '{file_check['suggestion']}' หรือไม่?",
                "requested_file": command["file"],
                "suggested_file": file_check["suggestion"]
            }
        LAST_USED_FILE = command["file"]

    action = command.get("action")
    result = None
    steps = []


    if action == "create_excel_file":
        filename = command.get("file", "new_file.xlsx")
        push_log(f"[Excel] สร้างไฟล์ใหม่: {filename}")
        steps.append(f"สร้างไฟล์ Excel: {filename}")
        if "ใช้โครงสร้าง" in user_command or "เหมือนไฟล์" in user_command:
            command["template_file"] = prev_last_used
            push_log(f"[Excel] ใช้โครงสร้างจากไฟล์: {prev_last_used}")
            steps.append(f"ใช้โครงสร้างจากไฟล์: {prev_last_used}")

        push_log(f"[Excel] กำลังสร้าง workbook...")
        result = create_excel_file(command)
        if command.get("data"):
            row_data = command.get("data", {})
            push_log(f"[Excel] เพิ่มข้อมูลแถวแรก...")
            append_result = append_row({"file": filename, "data": row_data})
            if append_result.get("status") == "success":
                result["preview"] = append_result.get("preview", [])
        push_log(f"[Excel] บันทึกไฟล์ {filename} สำเร็จ ✓")
        steps.append("ไฟล์ถูกสร้างเรียบร้อย")

    elif action == "append_row":
        push_log("[Intent] detect append previous search result")
        filename = command.get("file", "students.xlsx")
        data = command.get("data", {})

        file_info = ensure_file_path(filename)
        full_path = file_info["path"]

        push_log(f"[Excel] ตรวจสอบ {filename}")
        steps.append(f"เปิดไฟล์: {filename}")

        result = append_row_live(filename, data)

        steps.append("เพิ่มข้อมูลลง Excel แบบ realtime")

    elif action == "read_excel_file":
        filename = command.get("file", "students.xlsx")
        push_log(f"[Excel] อ่านไฟล์: {filename}")
        steps.append(f"อ่านไฟล์: {filename}")
        push_log(f"[Excel] โหลดข้อมูลจาก workbook...")
        result = read_excel_file(command)
        row_count = len(result.get("rows", [])) if isinstance(result, dict) else 0
        push_log(f"[Excel] อ่านสำเร็จ พบ {row_count} แถว ✓")
    
    elif action == "open_excel":
        push_log("[Excel] เปิด Excel application...")
        result = open_excel()
        steps.append("เปิด Excel สำเร็จ")

    elif action == "open_excel_file":
        fname = command.get('file', '')
        push_log(f"[Excel] เปิดไฟล์ {fname}...")
        result = open_excel_file(fname)
        steps.append(f"เปิดไฟล์ {fname} สำเร็จ")

    elif action == "search_excel":
        filename = command.get("file", "students.xlsx")
        keyword = command.get('keyword') or command.get('name') or command.get('query') or ""
        if not keyword.strip():
            keyword = extract_keyword(user_command)
        command['keyword'] = keyword
        push_log(f"[Excel] ค้นหาในไฟล์: {filename}")
        push_log(f"[Excel] keyword: {keyword}")
        steps.append(f"ค้นหาในไฟล์: {filename}")
        result = search_excel(command)
        row_count = len(result.get("rows", [])) if isinstance(result, dict) else 0
        push_log(f"[Excel] พบ {row_count} รายการ ✓")

    elif action == "search_student":
        push_log("[Brain] intent = search_student")
        keyword = command.get('keyword') or command.get('name') or command.get('query') or ""
        if not keyword.strip():
            keyword = extract_keyword(user_command)
        # Apply keyword correction using learned mappings and similarity
        corrected_keyword, correction_type, suggestions = get_corrected_keyword(keyword)
        command['keyword'] = corrected_keyword
        if correction_type == "exact":
            steps.append(f"ค้นหาฐานข้อมูล: {keyword} (แก้ไขจากแผนที่เรียนรู้: {corrected_keyword})")
        elif correction_type == "high":
            steps.append(f"ค้นหาฐานข้อมูล: {keyword} (แก้ไขอัตโนมัติด้วยความคล้ายสูง: {corrected_keyword})")
        else:  # low or none
            steps.append(f"ค้นหาฐานข้อมูล: {keyword}")
        
        push_log("[DB] เชื่อมต่อฐานข้อมูล...")
        push_log(f"[DB] ค้นหา keyword: {corrected_keyword}")
        data = search_student(command)
        row_count = data.get("count", len(data.get("rows", [])))
        push_log(f"[DB] พบ {row_count} รายการ")
        result = {
            "status": "success",
            "message": f"ค้นหา '{keyword}' ในฐานข้อมูลพบ {row_count} รายการ",
            "rows": data.get("rows", []),
            "count": row_count,
            "formatted": format_student_result(data),
            "keyword": keyword
        }
        # Add suggestions if correction_type is low
        if correction_type == "low" and suggestions:
            result["suggestions"] = suggestions
            result["guidance"] = f"ไม่พบข้อมูลที่ตรงกัน แต่คุณอาจหมายถึง: {', '.join(suggestions)}"
        global LAST_SEARCH_RESULTS
        if data.get("rows"):
            push_log("[Memory] บันทึก LAST_SEARCH_RESULTS")
            # Append new results to context memory (thread-safe)
            with _search_results_lock:
                for r in data["rows"]:
                    if r not in LAST_SEARCH_RESULTS:
                        LAST_SEARCH_RESULTS.append(r)
                if len(LAST_SEARCH_RESULTS) > 50:
                    LAST_SEARCH_RESULTS = LAST_SEARCH_RESULTS[-50:]  # Keep last 50 entries

    elif action == "append_student":
        push_log("[DB] เพิ่มข้อมูลลงใน Google Sheets...")
        steps.append("เพิ่มข้อมูลลงใน Google Sheets")
        result = append_student(command)
        push_log("[DB] บันทึกข้อมูลสำเร็จ ✓")

    elif action == "update_student":
        push_log("[DB] อัปเดตข้อมูลใน Google Sheets...")
        steps.append("อัปเดตข้อมูลใน Google Sheets")
        result = update_student(command)
        push_log("[DB] อัปเดตสำเร็จ ✓")

    elif action == "delete_student":
        push_log("[DB] ลบข้อมูลออกจาก Google Sheets...")
        steps.append("ลบข้อมูลออกจาก Google Sheets")
        result = delete_student(command)
        push_log("[DB] ลบสำเร็จ ✓")

    elif action == "read_database":
        push_log("[DB] เชื่อมต่อ Google Sheets...")
        steps.append("อ่านฐานข้อมูล (Google Sheets)")
        push_log("[DB] กำลังอ่านข้อมูลทั้งหมด...")
        data = read_database(command)
        row_count = len(data.get("rows", []))
        push_log(f"[DB] อ่านสำเร็จ พบ {row_count} รายการ ✓")
        result = {
            "status": "success",
            "message": f"อ่านฐานข้อมูลสำเร็จ",
            "rows": data.get("rows", []),
            "headers": data.get("headers", [])
        }

    elif action == "sync_db":
        push_log("[DB] เริ่ม sync ฐานข้อมูล Google Sheets...")
        steps.append("กำลังดึงข้อมูลทั้งหมดจาก Google Sheets...")
        push_log("[DB] เชื่อมต่อ Google Sheets API...")
        command["page_size"] = 10000
        push_log("[DB] ดึงข้อมูลทั้งหมด (page_size=10000)...")
        data = read_database(command)
        rows = data.get("rows", [])

        if not rows:
            push_log("[DB] ERROR: ดึงข้อมูลล้มเหลว หรือฐานข้อมูลว่างเปล่า", "error")
            return {
                "status": "error",
                "message": "ไม่สามารถดึงข้อมูลจาก Google Sheets ได้ หรือฐานข้อมูลว่างเปล่า ระบบจะไม่เขียนทับไฟล์เดิมเพื่อความปลอดภัย",
                "steps": steps + ["ดึงข้อมูลล้มเหลว"]
            }

        push_log(f"[DB] ดึงข้อมูลสำเร็จ {len(rows)} รายการ")
        push_log("[Memory] กำลังบันทึก db_cache.json...")
        cache_path = os.path.join(DATA_FOLDER, 'db_cache.json')
        try:
            if not os.path.exists(DATA_FOLDER):
                os.makedirs(DATA_FOLDER)
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(rows, f, ensure_ascii=False, indent=2)
            push_log(f"[Memory] บันทึก db_cache.json สำเร็จ ({len(rows)} รายการ) ✓")
            result = {
                "status": "success",
                "message": f"โหลดข้อมูลจากฐานข้อมูลเสร็จสิ้น บันทึกไว้ใน db_cache.json เรียบร้อยแล้ว (จำนวน {len(rows)} รายการ)",
                "rows": []
            }
        except Exception as e:
            push_log(f"[Memory] ERROR บันทึกไฟล์: {e}", "error")
            result = {"status": "error", "message": f"เกิดข้อผิดพลาดในการบันทึกไฟล์: {e}"}

    elif action == "list_files":
        push_log("[System] ค้นหาไฟล์ Excel ในโฟลเดอร์ data/...")
        steps.append("รายการไฟล์ Excel")
        files = search_excel_files()
        push_log(f"[System] พบ {len(files)} ไฟล์ ✓")
        result = {"status": "success", "files": files, "message": f"พบ {len(files)} ไฟล์"}

    elif action == "copy_data":
        push_log(f"[Excel] คัดลอกข้อมูลจาก {command.get('file')} → {command.get('dest_file')}...")
        result = copy_data(command)
        push_log("[Excel] คัดลอกข้อมูลสำเร็จ ✓")
        steps.append("คัดลอกข้อมูลสำเร็จ")

    elif action == "merge_files":
        push_log(f"[Excel] ผสานไฟล์ {command.get('file')} + {command.get('merge_file')}...")
        result = merge_files(command)
        push_log("[Excel] ผสานไฟล์สำเร็จ ✓")
        steps.append("ผสานไฟล์สำเร็จ")

    elif action == "summarize_data":
        push_log(f"[Brain] วิเคราะห์และสรุปข้อมูล {command.get('file')}...")
        result = summarize_data(command)
        push_log("[Brain] สรุปข้อมูลสำเร็จ ✓")
        steps.append("สรุปข้อมูลสำเร็จ")

    elif action == "get_statistics":
        push_log(f"[Brain] คำนวณสถิติ {command.get('file')}...")
        result = get_statistics(command)
        push_log("[Brain] คำนวณสถิติสำเร็จ ✓")
        steps.append("คำนวณสถิติสำเร็จ")

    elif action == "add_chart":
        push_log(f"[Excel] เพิ่มกราฟลงใน {command.get('file')}...")
        from tools.excel_tools import add_chart_to_excel
        result = add_chart_to_excel(command)
        push_log("[Excel] เพิ่มกราฟสำเร็จ ✓")
        steps.append("เพิ่มกราฟลงในไฟล์ Excel สำเร็จ")

    elif action == "analyze_file":
        push_log(f"[Brain] วิเคราะห์โครงสร้างไฟล์ {command.get('file')}...")
        file_info = ensure_file_path(command.get("file", "students.xlsx"))
        push_log("[Brain] ตรวจสอบ patterns และ relationships...")
        analysis = analyze_file_structure(os.path.join(DATA_FOLDER, file_info["filename"]))
        patterns = detect_patterns_and_relationships(analysis)
        push_log("[Brain] วิเคราะห์โครงสร้างไฟล์สำเร็จ ✓")
        result = {"status": "success", "analysis": analysis, "patterns": patterns}
        steps.append("วิเคราะห์โครงสร้างไฟล์สำเร็จ")

    elif action == "validate_data":
        push_log(f"[System] ตรวจสอบความถูกต้องของข้อมูล {command.get('file')}...")
        file_info = ensure_file_path(command.get("file", "students.xlsx"))
        is_valid, errors = validate_excel_data(os.path.join(DATA_FOLDER, file_info["filename"]))
        if is_valid:
            push_log("[System] ข้อมูลถูกต้องทั้งหมด ✓")
        else:
            push_log(f"[System] พบข้อผิดพลาด {len(errors)} รายการ", "warning")
        result = {"status": "success" if is_valid else "warning", "valid": is_valid, "errors": errors}
        steps.append("ตรวจสอบข้อมูลสำเร็จ")

    elif action == "export_csv":
        push_log(f"[Excel] ส่งออก {command.get('file')} เป็น CSV...")
        result = export_to_csv(command)
        push_log("[Excel] ส่งออก CSV สำเร็จ ✓")
        steps.append("ส่งออกเป็น CSV สำเร็จ")

    elif action == "export_html":
        push_log(f"[Excel] ส่งออก {command.get('file')} เป็น HTML...")
        result = export_to_html(command)
        push_log("[Excel] ส่งออก HTML สำเร็จ ✓")
        steps.append("ส่งออกเป็น HTML สำเร็จ")

    elif action == "dashboard":
        push_log(f"[Brain] สร้าง Dashboard จาก {command.get('file')}...")
        result = export_dashboard(command)
        push_log("[Brain] สร้าง Dashboard สำเร็จ ✓")
        steps.append("สร้างแดชบอร์ดสำเร็จ")

    if isinstance(result, dict):
        r = cast(Dict[str, Any], result)
        r["steps"] = steps
        
        # Calculate AI Confidence
        confidence = 0.95
        if r.get("status") == "error": confidence = 0.3
        r["confidence"] = confidence

        # Proactive Alerting (only when DB search truly returns zero rows)
        if action == "search_student":
            cnt = r.get("count")
            if cnt is None:
                cnt = len(r.get("rows", []))
            if cnt == 0:
                r["alert"] = "ANOMALY_DETECTED"
            
        try:
            brain.analyze_and_learn(user_command, action, r)
        except Exception as e:
            print(f"Brain analyze error: {e}")
            # Continue without analysis
        if "file" in command and isinstance(command, dict):
            r["filename"] = command["file"]
            if action in ["create_excel_file", "append_row", "update_row"]:
                try:
                    file_data = read_excel_file({"file": command["file"]})
                    if isinstance(file_data, dict) and file_data.get("status") == "success":
                        r["preview"] = file_data.get("rows", [])
                except: pass
    return result
