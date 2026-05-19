import json
with open('data/db_cache.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f'จำนวนนักเรียนทั้งหมด: {len(data)} คน')
print()

# แสดงตัวอย่างนักเรียน 3 คนแรก
for i, student in enumerate(data[:3]):
    name = f'{student.get("ชื่อ", "")} {student.get("สกุล", "")}'.strip()
    rank = student.get('ยศ', '')
    position = student.get('ตำแหน่ง', '')
    phone = student.get('เบอร์โทรศัพท์', '')
    print(f'{i+1}. {rank} {name}')
    print(f'   ตำแหน่ง: {position}')
    print(f'   เบอร์โทร: {phone}')
    print()