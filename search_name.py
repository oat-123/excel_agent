import json
import sys
import io
import locale

# Force UTF-8 for proper Thai display
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from tools.sheets_tools import get_sheet_data, find_header_row

data = get_sheet_data()
header_row = find_header_row(data)
rows = data[header_row + 1:]
headers = data[header_row]

# หาชื่อที่มี "ธีร" หรือ "ขาว"
found = []
for row in rows:
    record = {h: row[i] if i < len(row) else "" for i, h in enumerate(headers)}
    name = record.get("ชื่อ", "")
    last = record.get("สกุล", "")
    if "ธีร" in name or "ขาว" in last or "ศรี" in last:
        found.append(f"{name} {last}")

print(f"Found {len(found)} matches:")
for f in found[:10]:
    print(f)

# บันทึกไฟล์
with open('search_results.json', 'w', encoding='utf-8') as f:
    json.dump(found[:20], f, ensure_ascii=False, indent=2)
print("Saved to search_results.json")