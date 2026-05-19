import sys
sys.path.append('.')
from agent import process_command

# ทดสอบการค้นหาพร้อม spelling correction
result = process_command('ดูข้อมูล ภทธภูมิ ทาภักดี')
print(f'Status: {result.get("status")}')
print(f'Message: {result.get("message")}')
if result.get('rows'):
    print(f'พบ {len(result.get("rows", []))} รายการ')
    for row in result.get('rows', []):
        print(f'  ชื่อ: {row.get("ชื่อ")} {row.get("สกุล")}')
        print(f'  เบอร์โทร: {row.get("เบอร์โทรศัพท์")}')