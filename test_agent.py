import sys
sys.path.append('.')
from agent import process_command

# ทดสอบการค้นหาผ่าน agent ด้วย spelling ที่ต่างกัน
test_queries = ['ดูข้อมูล ธีรภัทร ขาวศรี', 'ดูข้อมูล ธีรภัทร์ ขาวศรี']

for query in test_queries:
    print(f'\n=== ทดสอบ: {query} ===')
    result = process_command(query)
    print(f'Status: {result.get("status")}')
    print(f'Message: {result.get("message")}')
    if result.get('rows'):
        print(f'พบ {len(result.get("rows", []))} รายการ')
        for row in result.get('rows', []):
            print(f'  ชื่อ: {row.get("ชื่อ")} {row.get("สกุล")}')
            print(f'  เบอร์โทร: {row.get("เบอร์โทรศัพท์")}')