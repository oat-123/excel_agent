import sys
import time
sys.path.append('.')
from agent import process_command

# ทดสอบ fast lookup ผ่าน agent
print("=== ทดสอบ Fast Lookup ===")
start = time.time()
result = process_command('ดูข้อมูล ธีรภัทร์ ขาวศรี')
end = time.time()

print(f'Status: {result.get("status")}')
print(f'Message: {result.get("message")}')
print(f'Time taken: {end - start:.4f} seconds')
if result.get('rows'):
    print(f'พบข้อมูล: {result.get("rows")[0].get("ชื่อ")} {result.get("rows")[0].get("สกุล")}')

print("\n=== ทดสอบ Spelling Correction ===")
start = time.time()
result2 = process_command('ดูข้อมูล ภทธภูมิ ทาภักดี')
end = time.time()

print(f'Status: {result2.get("status")}')
print(f'Message: {result2.get("message")}')
print(f'Time taken: {end - start:.4f} seconds')
if result2.get('rows'):
    print(f'พบข้อมูล: {result2.get("rows")[0].get("ชื่อ")} {result2.get("rows")[0].get("สกุล")}')