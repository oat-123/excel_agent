import sys
sys.path.append('.')
from memory.name_mapping import get_corrected_keyword

# ทดสอบระบบ name correction
test_cases = ['ธีรภัทร', 'ธีรภัทร์', 'ธีรภัทร ขาวศรี', 'ภัทธภูมิ', 'ทาภักดี']

for test in test_cases:
    result = get_corrected_keyword(test)
    print(f'get_corrected_keyword("{test}"): {result}')