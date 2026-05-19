"""
tools/desktop_tools.py — Win32COM Excel automation with realtime live logging.

append_row_live() writes one row into an open (or auto-opened) Excel workbook
cell-by-cell so the user can watch J.A.R.V.I.S. type in realtime.
"""
import subprocess
import os
import time
import pythoncom
import win32com.client

from utils.logger import push_log

# ---------------------------------------------------------------------------
# Column index → human-readable header mapping (matches students.xlsx schema)
# Extend this dict if your workbook has more columns.
# ---------------------------------------------------------------------------
_COL_NAMES = {
    1: "ลำดับ",
    2: "ยศ",
    3: "ชื่อ",
    4: "สกุล",
    5: "ชั้นปีที่",
    6: "ตำแหน่ง",
    7: "สังกัด",
    8: "เบอร์โทรศัพท์",
}


def open_excel():
    """Launch a blank Excel instance."""
    try:
        push_log("[Excel] เปิด Excel application...")
        subprocess.Popen(["start", "excel"], shell=True)
        push_log("[Excel] Excel เปิดสำเร็จ")
        return {"status": "success", "message": "Opened Excel successfully"}
    except Exception as e:
        push_log(f"[Excel] ERROR: {e}", "error")
        return {"status": "error", "message": str(e)}


def open_excel_file(filename: str):
    """Open a specific .xlsx file with the default application."""
    try:
        full_path = os.path.abspath(os.path.join("data", filename))
        push_log(f"[Excel] เปิดไฟล์ {filename}...")
        os.startfile(full_path)
        push_log(f"[Excel] เปิด {filename} สำเร็จ")
        return {"status": "success", "message": f"Opened {filename}"}
    except Exception as e:
        push_log(f"[Excel] ERROR เปิดไฟล์: {e}", "error")
        return {"status": "error", "message": str(e)}


def append_row_live(filename: str, data: dict) -> dict:
    """
    Append one row into an open (or auto-opened) Excel workbook using COM.

    Steps performed (each emits a push_log):
      1. CoInitialize COM
      2. GetActiveObject or Dispatch Excel
      3. Locate / open the target workbook
      4. Find last used row
      5. Copy format from previous row (PasteSpecial formats only)
      6. Write each cell value with a short delay (realtime visual effect)
      7. Save workbook
    """
    pythoncom.CoInitialize()

    try:
        # ── 1. Acquire Excel instance ────────────────────────────────────
        push_log("[Excel] ตรวจสอบ Excel instance...")
        try:
            excel = win32com.client.GetActiveObject("Excel.Application")
            push_log("[Excel] ใช้ Excel instance ที่เปิดอยู่")
        except Exception:
            push_log("[Excel] เปิด Excel instance ใหม่...")
            excel = win32com.client.Dispatch("Excel.Application")

        excel.Visible = True
        excel.WindowState = -4137  # xlMaximized

        # ── 2. Resolve full path ─────────────────────────────────────────
        full_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "data", filename)
        )
        push_log(f"[Excel] ตรวจสอบ {filename}")

        # ── 3. Find or open workbook ─────────────────────────────────────
        workbook = None
        for wb in excel.Workbooks:
            if os.path.abspath(wb.FullName).lower() == full_path.lower():
                workbook = wb
                break

        if workbook is None:
            push_log(f"[Excel] opening workbook: {filename}")
            workbook = excel.Workbooks.Open(full_path)
        else:
            push_log("[Excel] workbook เปิดอยู่แล้ว")

        workbook.Activate()
        sheet = workbook.ActiveSheet
        sheet.Activate()

        # ── 4. Find last used row ────────────────────────────────────────
        last_row = sheet.Cells(sheet.Rows.Count, 1).End(-4162).Row  # xlUp
        target_row = last_row + 1
        push_log(f"[Excel] last used row = {last_row}  →  writing row {target_row}")

        # ── 5. Copy format from previous row ────────────────────────────
        push_log("[Excel] copy format row ก่อนหน้า")
        sheet.Rows(last_row).Copy()
        sheet.Rows(target_row).PasteSpecial(-4122)  # xlPasteFormats
        excel.CutCopyMode = False  # clear clipboard marquee

        # ── 6. Write cells one-by-one (realtime) ────────────────────────
        values = list(data.values())
        for col_idx, value in enumerate(values, start=1):
            col_label = _COL_NAMES.get(col_idx, f"col{col_idx}")
            display_val = str(value) if value is not None else ""
            push_log(f"[Excel] writing {col_label} ({col_idx}) = {display_val}")
            cell = sheet.Cells(target_row, col_idx)
            cell.Value = value
            cell.Select()
            time.sleep(0.12)  # short pause for visual effect

        # ── 7. Save ──────────────────────────────────────────────────────
        push_log("[Excel] save workbook")
        workbook.Save()

        # Bring Excel to foreground
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
        push_log(f"[Excel] ERROR: {e}", "error")
        return {"status": "error", "message": str(e)}

    finally:
        pythoncom.CoUninitialize()
