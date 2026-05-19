# type: ignore
import pandas as pd
import os
import subprocess
import sys
import json as json_module
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from typing import Dict, List, Any, Optional, Tuple
# Define the data folder path
DATA_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'data')
UPLOAD_FOLDER = os.path.join(DATA_FOLDER, 'uploads')

# Validation Rules for Student Data
VALIDATION_RULES = {
    "ยศ": {"required": True, "pattern": r"^(นพ\.|น\.พ\.|ร\.อ\.|ร\.ท\.|ร\.ต\.|จ่อ\.|ส\.ท\.|ส\.ต\.|ส\.จ\.|โทร\.|พัน\.|ร้อย\.)"},
    "ชื่อ": {"required": True, "min_length": 1, "max_length": 50},
    "สกุล": {"required": True, "min_length": 1, "max_length": 50},
    "เบอร์โทรศัพท์": {"pattern": r"^0\d{8,9}$"},
}

def validate_student_data(data: Dict[str, Any], rules: Dict = None) -> Tuple[bool, List[str]]:
    """Validate student data against predefined rules"""
    errors = []
    rules = rules or VALIDATION_RULES
    
    for field, rule in rules.items():
        value = data.get(field, "")
        
        if rule.get("required") and not value:
            errors.append(f"{field} is required")
        
        if value and "min_length" in rule and len(str(value)) < rule["min_length"]:
            errors.append(f"{field} must be at least {rule['min_length']} characters")
        
        if value and "max_length" in rule and len(str(value)) > rule["max_length"]:
            errors.append(f"{field} must be at most {rule['max_length']} characters")
        
        if value and "pattern" in rule:
            import re
            str_val = str(value).strip()
            if not re.match(rule["pattern"], str_val):
                # Special handling for phone number: if it's all digits and length 9 or 10, 
                # we assume the user forgot the leading zero and accept it as valid.
                if field == "เบอร์โทรศัพท์" and str_val.isdigit() and len(str_val) in (9, 10):
                    # Accept as valid, no error added.
                    pass
                else:
                    errors.append(f"{field} format is invalid")
    
    return len(errors) == 0, errors

def validate_excel_data(filepath: str, sheet_name: str = "Sheet1") -> Tuple[bool, List[Dict]]:
    """Validate all rows in an Excel file"""
    if not os.path.exists(filepath):
        return False, [{"error": "File not found"}]
    
    errors = []
    hi, df = read_dataframe_with_header(filepath, sheet_name)
    df = slim_to_export_columns(df)
    
    for idx, row in df.iterrows():
        row_data = row.to_dict()
        is_valid, row_errors = validate_student_data(row_data)
        if not is_valid:
            errors.append({"row": idx + 1, "errors": row_errors})
    
    return len(errors) == 0, errors

import os
import win32com.client


import os
import time
import pythoncom
import win32com.client


def append_row_live(filename, data):
    """
    Append row into opened Excel workbook with realtime visual update
    and preserve previous row formatting.
    Only include columns A-J (จนถึง เบอร์โทรศัพท์).
    Column A (ลำดับ) auto-generates Thai numerals.
    """
    pythoncom.CoInitialize()

    try:
        # ใช้ excel instance เดิมก่อน
        try:
            excel = win32com.client.GetActiveObject("Excel.Application")
        except Exception:
            excel = win32com.client.Dispatch("Excel.Application")

        excel.Visible = True
        excel.WindowState = -4137   # maximize

        full_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "data",
                filename
            )
        )

        workbook = None

        # หา workbook ที่เปิดอยู่แล้ว
        for wb in excel.Workbooks:
            if os.path.abspath(wb.FullName).lower() == full_path.lower():
                workbook = wb
                break

        # ถ้ายังไม่เปิด
        if workbook is None:
            workbook = excel.Workbooks.Open(full_path)

        workbook.Activate()
        sheet = workbook.ActiveSheet
        sheet.Activate()

        # หา row ล่าสุดจริงจาก column A
        last_row = sheet.Cells(sheet.Rows.Count, 1).End(-4162).Row
        target_row = last_row + 1

        # copy format row ก่อนหน้า
        sheet.Rows(last_row).Copy()
        sheet.Rows(target_row).PasteSpecial(-4122)   # xlPasteFormats

        # กรองเฉพาะข้อมูล columns A-J (9 columns)
        # ลำดับ, ยศ, ชื่อ, สกุล, ชั้นปีที่, ตอน, ตำแหน่ง, สังกัด, เบอร์โทรศัพท์
        values = list(data.values())[:9]

        # col_idx = 1 = ลำดับ (auto-generate Thai numerals)
        # col_idx = 2-9 = other fields from data
        
        # Count existing rows to auto-generate sequence number
        data_start_row = 4  # Assume data starts at row 4 (after header)
        if target_row > data_start_row:
            seq_number = target_row - data_start_row + 1
        else:
            seq_number = 1

        # Convert to Thai numerals (๑๒๓๔๕๖๗๘๙๐)
        thai_digits = str.maketrans('0123456789', '๐๑๒๓๔๕๖๗๘๙')
        thai_seq = str(seq_number).translate(thai_digits)

        from utils.logger import push_log
        
        # Write cell by cell (realtime)
        col_idx = 1
        # Cell A (ลำดับ) = auto-generated Thai numeral
        push_log(f"[Excel] writing ลำดับ ({col_idx}) = {thai_seq}")
        cell = sheet.Cells(target_row, col_idx)
        cell.Value = thai_seq
        cell.Select()
        time.sleep(0.12)

        # Remaining columns (B-J)
        _COL_NAMES = {
            2: "ยศ",
            3: "ชื่อ",
            4: "สกุล",
            5: "ชั้นปีที่",
            6: "ตอน",
            7: "ตำแหน่ง",
            8: "สังกัด",
            9: "เบอร์โทรศัพท์",
        }

        for i, value in enumerate(values[1:] if len(values) > 1 else [], start=2):
            col_label = _COL_NAMES.get(i, f"col{i}")
            display_val = str(value) if value is not None else ""
            push_log(f"[Excel] writing {col_label} ({i}) = {display_val}")
            cell = sheet.Cells(target_row, i)
            cell.Value = value
            cell.Select()
            time.sleep(0.12)

        # Save workbook
        push_log("[Excel] save workbook")
        workbook.Save()

        # bring excel มาหน้า
        excel.Visible = True
        excel.WindowState = -4137
        try:
            excel.ActiveWindow.Activate()
        except Exception:
            pass
        sheet.Cells(target_row, 1).Select()

        push_log(f"[Done] เพิ่มข้อมูลแถว {target_row} ใน {filename} สำเร็จ ✓")

        return {
            "status": "success",
            "message": f"เพิ่มข้อมูลใน {filename} แบบ realtime สำเร็จ (แถว {target_row})",
        }

    except Exception as e:
        from utils.logger import push_log
        push_log(f"[Excel] ERROR: {e}", "error")
        return {
            "status": "error",
            "message": str(e)
        }

    finally:
        pythoncom.CoUninitialize()

def search_excel_files():
    """List all Excel files in the data folder"""
    import glob
    files = glob.glob(os.path.join(DATA_FOLDER, "*.xlsx"))
    return [os.path.basename(f) for f in files]


def find_similar_filename(filename):
    """Find similar filenames if the exact match doesn't exist"""
    import difflib
    files = search_excel_files()
    if not files:
        return None
    matches = difflib.get_close_matches(filename, files, n=3, cutoff=0.3)
    return matches[0] if matches else None


def ensure_file_path(command_file=None):
    """Ensure file path exists and return with suggested corrections"""
    requested_file = command_file or "students.xlsx"
    if not requested_file.endswith('.xlsx') and not requested_file.endswith('.csv') and not requested_file.endswith('.json'):
        requested_file += '.xlsx'
    full_path = os.path.join(DATA_FOLDER, requested_file)
    
    if os.path.exists(full_path):
        return {"filename": requested_file, "exists": True, "suggestion": None, "path": full_path}
    
    # Try to find similar filename
    suggestion = find_similar_filename(requested_file)
    if suggestion and suggestion != requested_file:
        return {"filename": requested_file, "exists": False, "suggestion": suggestion, "path": full_path}
    
    return {"filename": requested_file, "exists": False, "suggestion": None, "path": full_path}


STUDENT_BASE_COLS = ["ลำดับ", "ยศ", "ชื่อ", "สกุล", "ชั้นปีที่", "ตอน", "ตำแหน่ง", "สังกัด", "เบอร์โทรศัพท์"]
# Export to Excel: columns A–I (ลำดับ … เบอร์โทรศัพท์)
STUDENT_SHEET_EXPORT_COLS = STUDENT_BASE_COLS

HEADER_ROW_1BASE = 3
STUDENT_HEADER_ROW_0BASED = HEADER_ROW_1BASE - 1  # Excel row 3
DATA_START_ROW_1BASE = 4
TITLE_MERGE_END_COL = 10  # column J

SHEET_FONT_NAME = "TH Sarabun New"
SHEET_FONT_SIZE = 14

THAI_DIGITS = str.maketrans('0123456789', '๐๑๒๓๔๕๖๗๘๙')


def to_thai_numeral(n):
    """Convert integer to Thai numeral string (e.g. 1 → '๑', 12 → '๑๒')"""
    return str(n).translate(THAI_DIGITS)


def _sheet_font(bold=False):
    return Font(name=SHEET_FONT_NAME, size=SHEET_FONT_SIZE, bold=bold)


def slim_to_export_columns(df):
    """Keep only student columns (A–I); missing columns become empty."""
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=STUDENT_SHEET_EXPORT_COLS)
    out = pd.DataFrame()
    for c in STUDENT_SHEET_EXPORT_COLS:
        out[c] = df[c] if c in df.columns else ""
    return out


def read_dataframe_with_header(filepath, sheet_name="Sheet1"):
    """Returns (header_row_0based, dataframe)."""
    hi = find_data_header_row_index(filepath, sheet_name)
    df = pd.read_excel(filepath, sheet_name=sheet_name, header=hi)
    return hi, df


def save_xlsx_student_layout(filepath, sheet_name, df_export, title_text):
    """
    Row 1: merged A1:J1 — workbook title (filename).
    Row 2: merged A2:J2 — empty.
    Row 3: column headers A–J.
    Row 4+: data (A–J).
    TH Sarabun New 14 + center, no bold. Borders on all cells.
    """
    df_export = slim_to_export_columns(df_export)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name

    ws.merge_cells(
        start_row=1, start_column=1, end_row=1, end_column=TITLE_MERGE_END_COL
    )
    ws.cell(row=1, column=1, value=title_text or "")

    ws.merge_cells(
        start_row=2, start_column=1, end_row=2, end_column=TITLE_MERGE_END_COL
    )
    ws.cell(row=2, column=1, value=None)

    for col_idx, h in enumerate(STUDENT_SHEET_EXPORT_COLS, start=1):
        ws.cell(row=HEADER_ROW_1BASE, column=col_idx, value=h)

    total_rows = len(df_export)
    for r_off, row in enumerate(df_export.itertuples(index=False)):
        excel_row = DATA_START_ROW_1BASE + r_off
        for col_idx, val in enumerate(row, start=1):
            cell_val = val
            # Column A (ลำดับ): auto-generate Thai numerals counting down
            if col_idx == 1:
                cell_val = to_thai_numeral(r_off + 1)
            ws.cell(row=excel_row, column=col_idx, value=cell_val)

    last_row = HEADER_ROW_1BASE
    if len(df_export) > 0:
        last_row = DATA_START_ROW_1BASE + len(df_export) - 1

    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    for r in range(1, last_row + 1):
        max_col = TITLE_MERGE_END_COL if r <= 2 else len(STUDENT_SHEET_EXPORT_COLS)
        for c in range(1, max_col + 1):
            cell = ws.cell(row=r, column=c)
            cell.font = _sheet_font(bold=False)
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border

    ws.row_dimensions[1].height = 28
    ws.row_dimensions[HEADER_ROW_1BASE].height = 22

    col_widths = {"A": 10, "B": 8, "C": 14, "D": 16, "E": 10, "F": 10,
                  "G": 14, "H": 16, "I": 16, "J": 18}
    for letter, w in col_widths.items():
        ws.column_dimensions[letter].width = w

    wb.save(filepath)


def _use_student_layout_on_save(header_0based, requested_filename):
    """Use merged-title + row-4 headers layout when file is students.xlsx or already on that template."""
    if header_0based == STUDENT_HEADER_ROW_0BASED:
        return True
    return (requested_filename or "").lower() == "students.xlsx"


def ordered_columns_for_row(row_data):
    """Column order for DB / sheet rows: known keys first, then any extra keys."""
    if not row_data:
        return list(STUDENT_BASE_COLS)
    cols = [c for c in STUDENT_BASE_COLS if c in row_data]
    for k in row_data:
        if k not in cols:
            cols.append(k)
    return cols if cols else list(STUDENT_BASE_COLS)


def dataframe_columns_match_row(existing_df, row_data):
    """True if at least one real column name exists in row_data (not Unnamed / empty)."""
    if existing_df is None or len(existing_df.columns) == 0:
        return False
    for c in existing_df.columns:
        s = str(c).strip()
        if not s or s.lower().startswith("unnamed"):
            continue
        if s in row_data:
            return True
    return False


def find_data_header_row_index(filepath, sheet_name="Sheet1", max_scan=40):
    """
    0-based row index of the header row (row containing Thai column names like ชื่อ / สกุล).
    Standard student export: headers on Excel row 4 (index 3).
    """
    try:
        preview = pd.read_excel(filepath, sheet_name=sheet_name, header=None, nrows=max_scan)
    except Exception:
        return 0
    for i in range(len(preview)):
        vals = preview.iloc[i].astype(str).fillna("")
        row_text = " ".join(str(v) for v in vals if str(v).strip() and str(v) != "nan")
        if "ชื่อ" in row_text and "สกุล" in row_text:
            return i
    return 0


def close_excel_if_open(filepath):
    """Close Excel application if the file is open"""
    if sys.platform == "win32":
        try:
            # Check if Excel is running with the file
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq excel.exe'],
                capture_output=True, text=True
            )
            if 'excel.exe' in result.stdout:
                # Try to close the specific workbook
                try:
                    subprocess.run(['taskkill', '/IM', 'excel.exe', '/F'], capture_output=True)
                    import time
                    time.sleep(1)  # Wait for Excel to close
                except:
                    pass  # Ignore errors if file is already closed
        except:
            pass


def read_excel_file(command):
    file_info = ensure_file_path(command.get("file", "students.xlsx"))
    filename = os.path.join(DATA_FOLDER, file_info["filename"])
    sheet_name = command.get("sheet", "Sheet1")
    if not os.path.exists(filename):
        return {"error": f"file not found: {filename}"}
    header_idx = find_data_header_row_index(filename, sheet_name)
    df = pd.read_excel(filename, sheet_name=sheet_name, header=header_idx)
    return {
        "status": "success",
        "rows": df.fillna("").to_dict(orient="records")
    }


def apply_cell_style(cell, bold=False, fill=None, alignment=None, font_name="TH Sarabun New", font_size=14):
    """Apply consistent styling to a cell."""
    cell.font = Font(name=font_name, size=font_size, bold=bold)
    if alignment:
        cell.alignment = alignment
    if fill:
        cell.fill = fill

def create_excel_file(command):
    """
    Create a new Excel file optionally based on a template.
    """
    file_info = ensure_file_path(command.get("file", "new_file.xlsx"))
    filename = os.path.join(DATA_FOLDER, file_info["filename"])
    title_text = os.path.splitext(file_info["filename"])[0]
    row_data = command.get("data") or {}
    if row_data:
        slim = pd.DataFrame(
            [{c: row_data.get(c, "") for c in STUDENT_SHEET_EXPORT_COLS}]
        )
    else:
        slim = pd.DataFrame(columns=STUDENT_SHEET_EXPORT_COLS)
    save_xlsx_student_layout(filename, "Sheet1", slim, title_text)
    return {"status": "success", "message": f"Created file: {filename}", "preview": []}


def append_row(command):
    file_info = ensure_file_path(command.get("file", "students.xlsx"))
    filename = os.path.join(DATA_FOLDER, file_info["filename"])
    row_data = command.get("data", {})

    # realtime mode
    if command.get("live", False):
        from tools.desktop_tools import append_row_live
        return append_row_live(filename, row_data)

    sheet_name = command.get("sheet", "Sheet1")
    title_text = os.path.splitext(file_info["filename"])[0]
    new_row = {c: row_data.get(c, "") for c in STUDENT_SHEET_EXPORT_COLS}

    close_excel_if_open(filename)

    if os.path.exists(filename):
        try:
            _, existing_df = read_dataframe_with_header(filename, sheet_name)
            if row_data and not dataframe_columns_match_row(existing_df, row_data):
                existing_slim = pd.DataFrame(columns=STUDENT_SHEET_EXPORT_COLS)
            else:
                existing_slim = slim_to_export_columns(existing_df)

            final_df = pd.concat(
                [existing_slim, pd.DataFrame([new_row])],
                ignore_index=True
            )
        except Exception:
            final_df = pd.DataFrame([new_row])
    else:
        final_df = pd.DataFrame([new_row])

    save_xlsx_student_layout(filename, sheet_name, final_df, title_text)

    return {
        "status": "success",
        "message": f"Added row to {filename}",
        "preview": final_df.fillna("").to_dict(orient="records"),
    }

def find_duplicates(command):
    file_info = ensure_file_path(command.get("file", "students.xlsx"))
    filename = os.path.join(DATA_FOLDER, file_info["filename"])
    column = command.get("column")
    if not os.path.exists(filename): return {"error": "file not found"}
    hi, df = read_dataframe_with_header(filename, command.get("sheet", "Sheet1"))
    if _use_student_layout_on_save(hi, file_info["filename"]):
        df = slim_to_export_columns(df)
    if column not in df.columns: return {"error": f"column '{column}' not found"}
    duplicates = df[df.duplicated(subset=[column], keep=False)]
    return {"status": "success", "duplicate_count": len(duplicates), "rows": duplicates.fillna("").to_dict(orient="records")}

def delete_row(command):
    file_info = ensure_file_path(command.get("file", "students.xlsx"))
    filename = os.path.join(DATA_FOLDER, file_info["filename"])
    sheet_name = command.get("sheet", "Sheet1")
    search_column = command.get("search_column")
    search_value = command.get("search_value")
    if not os.path.exists(filename): return {"error": "file not found"}
    hi, df = read_dataframe_with_header(filename, sheet_name)
    use_layout = _use_student_layout_on_save(hi, file_info["filename"])
    if use_layout:
        df = slim_to_export_columns(df)
    df = df[df[search_column].astype(str) != str(search_value)]
    title_text = os.path.splitext(file_info["filename"])[0]
    if use_layout:
        save_xlsx_student_layout(filename, sheet_name, df, title_text)
    else:
        df.to_excel(filename, index=False)
    return {"status": "success", "message": f"Deleted from {filename}"}

def update_row(command):
    file_info = ensure_file_path(command.get("file", "students.xlsx"))
    filename = os.path.join(DATA_FOLDER, file_info["filename"])
    sheet_name = command.get("sheet", "Sheet1")
    search_column = command.get("search_column")
    search_value = command.get("search_value")
    update_column = command.get("update_column")
    new_value = command.get("new_value")
    if not os.path.exists(filename): return {"error": "file not found"}
    hi, df = read_dataframe_with_header(filename, sheet_name)
    use_layout = _use_student_layout_on_save(hi, file_info["filename"])
    if use_layout:
        df = slim_to_export_columns(df)
    df.loc[df[search_column].astype(str) == str(search_value), update_column] = new_value
    title_text = os.path.splitext(file_info["filename"])[0]
    if use_layout:
        save_xlsx_student_layout(filename, sheet_name, df, title_text)
    else:
        df.to_excel(filename, index=False)
    return {"status": "success", "message": "Updated successfully"}

def search_excel(command):
    file_info = ensure_file_path(command.get("file", "students.xlsx"))
    filename = os.path.join(DATA_FOLDER, file_info["filename"])
    keyword = command.get("keyword", "")
    if not os.path.exists(filename): return {"error": "file not found"}
    hi, df = read_dataframe_with_header(filename, command.get("sheet", "Sheet1"))
    if _use_student_layout_on_save(hi, file_info["filename"]):
        df = slim_to_export_columns(df)
    # Filter to only A-J columns
    df = df.iloc[:, :9]
    result = df[df.astype(str).apply(lambda row: row.str.contains(keyword, case=False).any(), axis=1)]
    return {"status": "success", "rows": result.fillna("").to_dict(orient="records")}

def copy_data(command):
    file_info = ensure_file_path(command.get("file", "students.xlsx"))
    filename = os.path.join(DATA_FOLDER, file_info["filename"])
    dest_file = command.get("dest_file", "copy.xlsx")
    if not os.path.exists(filename): return {"error": "file not found"}
    hi, df = read_dataframe_with_header(filename, command.get("sheet", "Sheet1"))
    use_layout = _use_student_layout_on_save(hi, file_info["filename"])
    if use_layout:
        df = slim_to_export_columns(df)
    df = df.iloc[:, :9]  # Limit to A-J
    dest_path = os.path.join(DATA_FOLDER, dest_file)
    dest_title = os.path.splitext(dest_file)[0]
    if use_layout:
        save_xlsx_student_layout(dest_path, "Sheet1", df, dest_title)
    else:
        df.to_excel(dest_path, index=False)
    return {"status": "success", "message": f"Copied to {dest_file}"}

def merge_files(command):
    file_info = ensure_file_path(command.get("file", "students.xlsx"))
    filename = os.path.join(DATA_FOLDER, file_info["filename"])
    merge_file = command.get("merge_file", "")
    merge_path = os.path.join(DATA_FOLDER, merge_file)
    if not os.path.exists(filename) or not os.path.exists(merge_path):
        return {"error": "files not found"}
    hi1, df1 = read_dataframe_with_header(filename, command.get("sheet", "Sheet1"))
    hi2, df2 = read_dataframe_with_header(merge_path, command.get("sheet", "Sheet1"))
    use_layout = _use_student_layout_on_save(hi1, file_info["filename"]) or _use_student_layout_on_save(
        hi2, merge_file
    )
    if use_layout:
        df1 = slim_to_export_columns(df1)
        df2 = slim_to_export_columns(df2)
    df1 = df1.iloc[:, :9]
    df2 = df2.iloc[:, :9]
    merged = pd.concat([df1, df2], ignore_index=True)
    title_text = os.path.splitext(file_info["filename"])[0]
    if use_layout:
        save_xlsx_student_layout(filename, command.get("sheet", "Sheet1"), merged, title_text)
    else:
        merged.to_excel(filename, index=False)
    return {"status": "success", "message": "Merged successfully"}

def convert_format(command):
    file_info = ensure_file_path(command.get("file", "students.xlsx"))
    filename = os.path.join(DATA_FOLDER, file_info["filename"])
    output_format = command.get("format", "csv").lower()
    if not os.path.exists(filename): return {"error": "file not found"}
    hi, df = read_dataframe_with_header(filename, command.get("sheet", "Sheet1"))
    if _use_student_layout_on_save(hi, file_info["filename"]):
        df = slim_to_export_columns(df)
    df = df.iloc[:, :9]  # Limit to A-J
    base_name = file_info["filename"].replace(".xlsx", "")
    output_file = f"{base_name}.{output_format}"
    output_path = os.path.join(DATA_FOLDER, output_file)
    if output_format == "csv":
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
    elif output_format == "json":
        df.to_json(output_path, orient="records", force_ascii=False)
    return {"status": "success", "message": f"Converted to {output_format.upper()}", "output_file": output_file}

def summarize_data(command):
    file_info = ensure_file_path(command.get("file", "students.xlsx"))
    filename = os.path.join(DATA_FOLDER, file_info["filename"])
    if not os.path.exists(filename): return {"error": "file not found"}
    hi, df = read_dataframe_with_header(filename, command.get("sheet", "Sheet1"))
    if _use_student_layout_on_save(hi, file_info["filename"]):
        df = slim_to_export_columns(df)
    df = df.iloc[:, :9]  # Limit to A-J
    summary = {"total_rows": len(df), "columns": list(df.columns), "text_summary": {}}
    for col in df.select_dtypes(include=['object']).columns[:5]:
        summary["text_summary"][col] = {"unique_values": int(df[col].nunique())}
    return {"status": "success", "summary": summary}

def get_statistics(command):
    file_info = ensure_file_path(command.get("file", "students.xlsx"))
    filename = os.path.join(DATA_FOLDER, file_info["filename"])
    if not os.path.exists(filename): return {"error": "file not found"}
    hi, df = read_dataframe_with_header(filename, command.get("sheet", "Sheet1"))
    if _use_student_layout_on_save(hi, file_info["filename"]):
        df = slim_to_export_columns(df)
    df = df.iloc[:, :9]  # Limit to A-J
    stats = {"row_count": len(df), "missing_data": {}}
    for col in df.columns:
        missing = df[col].isna().sum()
        if missing > 0: stats["missing_data"][col] = int(missing)
    return {"status": "success", "statistics": stats}

def add_chart_to_excel(command):
    file_info = ensure_file_path(command.get("file", "students.xlsx"))
    filename = os.path.join(DATA_FOLDER, file_info["filename"])
    if not os.path.exists(filename): return {"error": "file not found"}
    from openpyxl.chart import BarChart, Reference
    wb = openpyxl.load_workbook(filename)
    ws = wb.active
    if ws.max_row < DATA_START_ROW_1BASE:
        wb.close()
        return {"error": "No data rows below header; cannot add chart"}
    chart = BarChart()
    data = Reference(
        ws,
        min_col=2,
        min_row=HEADER_ROW_1BASE,
        max_row=ws.max_row,
        max_col=min(3, TITLE_MERGE_END_COL),
    )
    cats = Reference(
        ws,
        min_col=1,
        min_row=DATA_START_ROW_1BASE,
        max_row=ws.max_row,
    )
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    ws.add_chart(chart, "L2")
    wb.save(filename)
    return {"status": "success", "message": "Chart added"}

def save_uploaded_file(file_content, filename=None):
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    if not filename: filename = f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    with open(filepath, 'wb') as f: f.write(file_content)
    return filepath

def analyze_file_structure(filepath):
    if not os.path.exists(filepath): return {"error": "file not found"}
    excel_file = pd.ExcelFile(filepath)
    analysis = {"file_path": filepath, "sheets": []}
    for name in excel_file.sheet_names:
        df = pd.read_excel(filepath, sheet_name=name)
        df = df.iloc[:, :9]  # Limit to A-J
        analysis["sheets"].append({"name": name, "rows": len(df), "column_info": [{"name": str(c)} for c in df.columns[:9]]})
    return analysis

def detect_patterns_and_relationships(analysis):
    return {"has_headers": True, "data_patterns": []}

def learn_from_file_content(filepath, analysis, brain=None):
    """Extract knowledge from file content to learn patterns"""
    knowledge = {"column_types": {}}
    for sheet in analysis.get("sheets", []):
        sheet_name = sheet.get("name", "unknown")
        for col_info in sheet.get("column_info", []):
            col_name = col_info.get("name", "")
            if brain: brain._extract_entities(f"{sheet_name} {col_name}")
    return knowledge

def export_to_csv(command):
    """Export Excel file to CSV format"""
    file_info = ensure_file_path(command.get("file", "students.xlsx"))
    filename = os.path.join(DATA_FOLDER, file_info["filename"])
    if not os.path.exists(filename): return {"error": "file not found"}
    hi, df = read_dataframe_with_header(filename, command.get("sheet", "Sheet1"))
    df = slim_to_export_columns(df)
    df = df.iloc[:, :9]  # Limit to A-J
    base_name = file_info["filename"].replace(".xlsx", "")
    output_file = f"{base_name}.csv"
    output_path = os.path.join(DATA_FOLDER, output_file)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return {"status": "success", "message": f"Exported to {output_file}", "output_file": output_file}

def export_to_html(command):
    """Export Excel file to HTML format"""
    file_info = ensure_file_path(command.get("file", "students.xlsx"))
    filename = os.path.join(DATA_FOLDER, file_info["filename"])
    if not os.path.exists(filename): return {"error": "file not found"}
    hi, df = read_dataframe_with_header(filename, command.get("sheet", "Sheet1"))
    df = slim_to_export_columns(df)
    df = df.iloc[:, :9]  # Limit to A-J
    base_name = file_info["filename"].replace(".xlsx", "")
    output_file = f"{base_name}.html"
    output_path = os.path.join(DATA_FOLDER, output_file)
    html_content = df.to_html(index=False, escape=False, classes="excel-table")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"<!DOCTYPE html><html><head><title>{base_name}</title>")
        f.write("<style>.excel-table{border-collapse:collapse;width:100%;} .excel-table th,.excel-table td{border:1px solid #ddd;padding:8px;text-align:left;} .excel-table th{background-color:#4C5859;color:white;}</style>")
        f.write("</head><body>" + html_content + "</body></html>")
    return {"status": "success", "message": f"Exported to {output_file}", "output_file": output_file}

def export_dashboard(command):
    """Generate a summary dashboard for Excel data"""
    file_info = ensure_file_path(command.get("file", "students.xlsx"))
    filename = os.path.join(DATA_FOLDER, file_info["filename"])
    if not os.path.exists(filename): return {"error": "file not found"}
    hi, df = read_dataframe_with_header(filename, command.get("sheet", "Sheet1"))
    df = slim_to_export_columns(df)
    df = df.iloc[:, :9]  # Limit to A-J
    
    dashboard = {
        "total_records": len(df),
        "total_columns": len(df.columns),
        "columns": list(df.columns),
        "column_stats": {}
    }
    
    for col in df.columns:
        col_data = df[col].dropna()
        dashboard["column_stats"][col] = {
            "non_null_count": len(col_data),
            "null_count": len(df) - len(col_data),
            "unique_values": col_data.nunique() if len(col_data) > 0 else 0
        }
    
    return {"status": "success", "dashboard": dashboard}
