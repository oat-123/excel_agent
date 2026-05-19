import sys
sys.path.append('.')
from agent import process_command

# ทดสอบกรณีที่มี suggestions
result = process_command('ดูข้อมูล ธีรภัทร พรมมร')
print(f'Status: {result.get("status")}')
print(f'Message: {result.get("message")}')
if result.get('guidance'):
    print(f'Guidance: {result.get("guidance")}')
if result.get('suggestions'):
    print(f'Suggestions: {result.get("suggestions")}')