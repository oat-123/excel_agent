import sys
sys.path.append('.')
from tools.sheets_tools import search_student

# ทดสอบ fast lookup สำหรับชื่อที่ถูกต้อง 100%
import time

start = time.time()
result = search_student({'keyword': 'ธีรภัทร์ ขาวศรี'})
end = time.time()

print(f'Fast lookup result: {result}')
print(f'Time taken: {end - start:.4f} seconds')

# ทดสอบ partial match สำหรับกรณีอื่น
start = time.time()
result2 = search_student({'keyword': 'ภัทธภูมิ'})
end = time.time()

print(f'Partial match result: {result2}')
print(f'Time taken: {end - start:.4f} seconds')