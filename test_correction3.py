import sys
sys.path.append('.')
from memory.name_mapping import get_corrected_keyword

# ทดสอบ "ธีรภัทร ขาวศรี"
result = get_corrected_keyword('ธีรภัทร ขาวศรี')
print(f'get_corrected_keyword("ธีรภัทร ขาวศรี"): {result}')

# ทดสอบ "ธีรภัทร์ ขาวศรี"
result2 = get_corrected_keyword('ธีรภัทร์ ขาวศรี')
print(f'get_corrected_keyword("ธีรภัทร์ ขาวศรี"): {result2}')