import sys
sys.path.append('.')
from agent import process_command

# ทดสอบด้วย exception handling
try:
    result = process_command('ดูข้อมูล ธีรภัทร์ ขาวศรี')
    print(f'Status: {result.get("status")}')
    print(f'Message: {result.get("message")}')
    if result.get('rows'):
        print(f'พบ {len(result.get("rows", []))} รายการ')
        for row in result.get('rows', []):
            print(f'  ชื่อ: {row.get("ชื่อ")} {row.get("สกุล")}')
except Exception as e:
    print(f'Exception: {e}')
    import traceback
    traceback.print_exc()