import sys
import time
sys.path.append('.')
from agent import process_command

# ทดสอบทั้งสอง spelling
test_cases = ['ดูข้อมูล ธีรภัทร ขาวศรี', 'ดูข้อมูล ธีรภัทร์ ขาวศรี']

for case in test_cases:
    print(f'\n=== ทดสอบ: {case} ===')
    start = time.time()
    result = process_command(case)
    end = time.time()

    print(f'Status: {result.get("status")}')
    print(f'Message: {result.get("message")}')
    print(f'Time: {end - start:.4f} seconds')

    if result.get('rows'):
        row = result.get('rows')[0]
        print(f'ชื่อ: {row.get("ชื่อ")} {row.get("สกุล")}')
        print(f'เบอร์: {row.get("เบอร์โทรศัพท์")}')